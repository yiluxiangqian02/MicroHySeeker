using Newtonsoft.Json;
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.IO.Ports;
using System.Linq;
using System.Windows.Forms;

namespace eChemSDL
{
    public class SingleSolution
    {
        public string Solute { get; set; }
        public double LowConc { get; set; }
        public bool IsSolvent { get; set; }
        public bool InConstConc { get; set; }
        public int InjectOrder { get; set; }
        public int ChannelIndex { get; set; }//必须用一个变量对应通道！

        public SingleSolution(int channelindex, double conc, bool issolvent)
        {
            ChannelIndex = channelindex;
            Solute = LIB.CHs[ChannelIndex].ChannelName;
            LowConc = conc;
            IsSolvent = issolvent;
            InConstConc = true;
            InjectOrder = 0;
        }
    }

    public static class LIB
    {
        static LIB()
        {
            VAPoints.Add(new PointF(0, 0));
        }



        //public class FlushingChannel
        //{
        //    public MotorsOnRS485 PeristalticPumps;
        //    public int NumberOfPumps { get; set; }
        //    public float RPM { get; set; }
        //}

        public class PeriPumpSettings
        {
            public string PumpName { get; set; }
            public byte Address { get; set; }
            public ushort PumpRPM { get; set; }
            public PumpDirection Direction { get; set; }
            public MotorRS485.MotorState PumpStatus { get; set; }
            public enum PumpDirection
            {
                //[Description("闲置")]
                idle,
                //[Description("正转")]
                forward,
                //[Description("反转")]
                reverse
                //[Description("双向")]
                //two_way
            }
            public int CycleDuration { get; set; }//每段运行时间，秒钟，可用可不用
            public void DefaultSettings()
            {
                PumpRPM = Properties.Settings.Default.DefaultFlusherRPM;
                Direction = PumpDirection.forward; //默认正转
                Address = 255;
                CycleDuration = Properties.Settings.Default.DefaultFlusherDuration; //默认运行时间
                PumpStatus = new MotorRS485.MotorState
                {
                    IsRunning = false,
                };
            }
        }

        public static void CreateDefalutPPs()
        {
            byte[] addresses = LIB.RS485Driver.GetAddressBytes();

            //首次运行采用默认设置，三个泵，取最后3个地址
            PeriPumpSettings inlet = new PeriPumpSettings { PumpName = "Inlet" };
            PeriPumpSettings outlet = new PeriPumpSettings { PumpName = "Outlet" };
            PeriPumpSettings transfer = new PeriPumpSettings { PumpName = "Transfer" };
            inlet.DefaultSettings();
            outlet.DefaultSettings();
            transfer.DefaultSettings();
            PPs.Add(inlet);
            PPs.Add(outlet);
            PPs.Add(transfer);
            Console.WriteLine("LIB line97: CreateDefalutPPs");
            if (addresses.Length >= 3)
            {
                inlet.Address = addresses[addresses.Length - 3];
                outlet.Address = addresses[addresses.Length - 2];
                transfer.Address = addresses[addresses.Length - 1];
            }
        }

        //以下这个方法是添加了读取enum格式数据中的Description功能，在整个程序内都可以调用
        public static string GetDescription(this Enum currentEnum)
        {
            string description = String.Empty;
            DescriptionAttribute da;

            System.Reflection.FieldInfo fi = currentEnum.GetType().
                        GetField(currentEnum.ToString());
            da = (DescriptionAttribute)Attribute.GetCustomAttribute(fi,
                        typeof(DescriptionAttribute));
            if (da != null)
                description = da.Description;
            else
            {
                description = currentEnum.ToString();
                string value;
                if (LIB.NamedStrings.TryGetValue(description, out value))
                    description = value; //多语言化如果有值，就取值，没有就默认
            }

            return description;
        }

        public class ChannelSettings
        {
            public string ChannelName { get; set; }
            public double HighConc { get; set; }
            public ushort PumpSpeed { get; set; } //单位是RPM
            public Color ChannelColor { get; set; }
            public byte Address { get; set; } //RS485地址
            public double TubeInnerDiameter { get; set; } //通道内径，单位mm，估算DivperML
            public double WheelDiameter { get; set; } //蠕动泵辊轮直径，单位mm
            public int DivpermL { get; set; } //关键参数，电机输送的每毫升液体需要多少个编码值（一圈是16384）

            public ChannelSettings()
            {
                ChannelName = "Channel 1";
                HighConc = 1.0; //默认浓度
                PumpSpeed = 100; //默认转速100RPM
                ChannelColor = Color.Blue;
                Address = 255; //默认地址1
                TubeInnerDiameter = Properties.Settings.Default.DefaultTubeDiameter; 
                WheelDiameter = Properties.Settings.Default.DefaultWheelDiameter; 
                DivpermL = Properties.Settings.Default.DefaultDivPerML; 
            }

            public void DefaultSettings()
            {
                if (HighConc == 0)
                    HighConc = 1.0;
                if(PumpSpeed == 0)
                    PumpSpeed = 100; //默认转速100RPM
                if (TubeInnerDiameter == 0)
                    TubeInnerDiameter = Properties.Settings.Default.DefaultTubeDiameter;
                if (WheelDiameter == 0)
                    WheelDiameter = Properties.Settings.Default.DefaultWheelDiameter;
                if (DivpermL == 0)
                    DivpermL = Properties.Settings.Default.DefaultDivPerML;
            }
        }

        public static void CreateDefaultCHs()
        {
            byte[] addresses = LIB.RS485Driver.GetAddressBytes();
            if(addresses.Length >= 3)
            {
                Console.WriteLine("LIB line170: CreateDefalutCHs");
                for (int i = 0; i <= addresses.Count() - 3; i++)
                {
                    LIB.ChannelSettings ch = new LIB.ChannelSettings();
                    ch.DefaultSettings();
                    ch.Address = addresses[i];
                    LIB.CHs.Add(ch);//添加稀释器设置
                    Diluter diluter = new Diluter(ch);//添加实际稀释器
                    LIB.Diluters.Add(diluter);
                }
            }
        }

        //统一处理设备返回的消息，并负责转发接收到的对应的泵
        public static void DispatchPumpMessage(byte[] message)
        {
            if (message.Length >= 3 && message[0] == 0xFB)
            {
                //Console.WriteLine(BitConverter.ToString(message));
                byte addr = message[1];
                //注意：以下只转发到配液通道，如果需要转发到移液通道需要添加另外代码
                foreach (var diluter in Diluters)
                {
                    if (diluter.Address == addr)
                    {
                        diluter.HandleResponse(message);
                        break;
                    }
                }
                //TODO:转发到移液通道
            }
        }

        public class MixedSolution
        {
            public double TotalVol { get; set; }
            public double CurrentVol { get; set; }
            public Color SolColor { get; set; }
            public List<SingleSolution> SoluteList = new List<SingleSolution>();
            public string Solvent;

            public double SolventVol()
            {
                if (SoluteList.Count == 0)
                    return -1;
                double vol = 0;

                for (int i = 0; i < SoluteList.Count; i++)
                {
                    //if(!SolvatesList[i].IsSolvent)//SolvateList里面没有添加溶剂
                    //vol += SolvatesList[i].LowConc / SharedComponents.CHs[i].HighConc * TotalVol;//这句是重大错误！实际的溶质列表和通道列表完全不一样！不能直接用i对应！
                    vol += SoluteList[i].LowConc / LIB.CHs[SoluteList[i].ChannelIndex].HighConc * TotalVol;
                }
                return (TotalVol - vol);
            }
        }
        
        //public static string LogMsg;
        public static int DefaultCombCount = 10;//默认组合实验数目
        public static List<string> AvailablePorts = new List<string>();
        public static List<Diluter> Diluters = new List<Diluter>();
        public static MixedSolution MixedSol = new MixedSolution();
        public static MixedSolution WorkingElectrolyte = new MixedSolution();
        public static ExpProgram LastExp = new ExpProgram();//定义在Experiment.cs
        public static Flusher TheFlusher; // new Flusher();
        //public static MotorsOnRS485 RS485Controller; //只能有一个实例，只能创建一次
        public static MotorRS485 RS485Driver; //只能有一个实例，只能创建一次
        public static bool CHIConnected = false;
        public static CHInstrument CHI;//定义在Experiment.cs
        public static List<PointF> VAPoints = new List<PointF>();
        public static string DataFilePath;
        public static string ExpIDString;
        public static bool EngineeringMode;
        public static Dictionary<string, string> NamedStrings = new Dictionary<string, string>();
        public static Positioner ThePositioner; //注意：这个只是声明，在程序装载时构造。

        //public static BindingList<DefaultSolvateColor> solcols = new BindingList<DefaultSolvateColor>();
        public static BindingList<ChannelSettings> CHs = new BindingList<ChannelSettings>();
        public static BindingSource CHsettingsSource = new BindingSource(CHs, null);//为设置对话框里的gridview定义绑定数据
        public static BindingList<PeriPumpSettings> PPs = new BindingList<PeriPumpSettings>();
        public static BindingSource PPSettingsSource = new BindingSource(PPs, null);
        //public static SaveAsExcel ExcelDataFile;

        public static T Clone<T>(T source)
        {
            var serialized = JsonConvert.SerializeObject(source);
            return JsonConvert.DeserializeObject<T>(serialized);
        }
    }

    public static class LogMsgBuffer
    {
        public static string MsgBuffer = "";
        public static void AddEntry(string LogType, string Message)
        {
            MsgBuffer += "[" + LogType + "] " + DateTime.Now + " " + Message + "\r\n";
        }
        public static string GetContent()
        {
            string content;
            content = string.Copy(MsgBuffer);
            MsgBuffer = "";
            return content;
        }
        public static bool HasContent()
        {
            return MsgBuffer.Length > 0;
        }
    }

}
