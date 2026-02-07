using System;
using System.Drawing;
using System.IO.Ports;
using System.Linq;
using System.Timers;
using System.Threading.Tasks;

namespace eChemSDL
{
    public class Diluter
    {
        public string Name { get; set; }
        public double HighConc { get; set; }
        public double LowConc { get; set; }
        public double TotalVol { get; set; }
        public double PartVol { get; set; }
        public Color ChannelColor { get; set; }
        public string TestMsg { get; set; }


        //使用RS485Driver进行配液的新代码
        private MotorRS485 Controller;
        public byte Address;
        private double tubeInnerDiameter;
        private double wheelDiameter;
        private int divpermL; //每毫升液体需要多少个编码值（一圈是16384）
        private ushort speed; //转速，单位rpm
        private bool infusing = false; //是否正在注射
        private bool infused = false; //是否已经注射完成
        private bool failed = false;//是否注射失败
        private DateTime starttime;

        public Diluter(LIB.ChannelSettings ch)
        {
            Initialize(ch);
            //Controller.OnMessageReceived += Motor_Response;
        }

        //用SetCon初始化注射量，diluter是不同步骤公用的，开始先用SetCon计算各通道用时，保存在步骤变量中，执行时再用MakeCon重新计算当前注射量并动作。
        //public void SetConc(double conc)
        //{
        //    double vol;
        //    LowConc = conc;
        //    vol = TotalVol * LowConc / HighConc;
        //    SetVol(vol);
        //}

        //public void Dispense()
        //{
        //    DiluterTimer.Elapsed += ActivatePump;
        //    DiluterTimer.Interval = 10;
        //    DiluterTimer.Start();
        //    starttime = DateTime.Now;
        //}

        public void Infuse()
        {
            int divs = (int)Math.Round(PartVol * divpermL); //每毫升液体需要多少个编码值

            if (Controller == null || !Controller.IsReady)
            {
                // 控制器不可用，记录错误并设置失败标志
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "Error",
                    $"{Name}: RS485 controller not ready for address {Address}.");
                failed = true;
                return;
            }

            try
            {
                // 发送命令（异步），捕获可能发生的故障并记录
                var cmdTask = Controller.TurnTo(Address, divs);
                cmdTask.ContinueWith(t =>
                {
                    if (t.IsFaulted)
                    {
                        var ex = t.Exception?.GetBaseException();
                        LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "Error",
                            $"{Name}: failed to send command to pump {Address}: {ex?.Message}");
                        failed = true;
                    }
                }, TaskScheduler.Default);
            }
            catch (Exception ex)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "Error",
                    $"{Name}: exception when sending command to pump {Address}: {ex.Message}");
                failed = true;
            }
        }

        public double GetDuration()
        {
            return PartVol * divpermL / 16384.0 / speed * 60; //返回秒数
        }

        /// <summary>开始配液前需要把浓度或体积转递给注射通道，issolvent表示是否是溶剂，solvenvolt表示溶剂体积。</summary>
        public void Prepare(double targetconc, bool issolvent, double solvenvolt)
        {
            LowConc = targetconc;
            if (issolvent)
                PartVol = solvenvolt; //如果是溶剂，直接使用传入的体积
            else
                PartVol = TotalVol * targetconc / HighConc; //计算注射体积
        }

        public void HandleResponse(byte[] message)
        {
            //Console.WriteLine(BitConverter.ToString(message));
            if (message[0] == 0xFB && message[1] == Address && message[2]==0xF4)
            {
                if (message[3] == 0x01)
                {
                    Console.WriteLine(Name + "开始注射");
                    starttime = DateTime.Now;
                    infusing = true; //正在注射
                }
                else if (message[3] == 0x02)//开始居然忘记了前面这个else，导致逻辑错误，注射开始刚把infusing设置为true，结果马上又被设置为false了
                {
                    infusing = false; //注射完成
                    infused = true;
                    Console.WriteLine(Name + "完成注射");
                }
                else
                {
                    infusing = false; //注射失败
                    Console.WriteLine(Name + "其他信息");
                    Console.WriteLine(BitConverter.ToString(message));
                    infused = false;
                    failed = true;
                }
            }
        }

        //private void ActivatePump(Object source, ElapsedEventArgs e)
        //{
        //    //
        //    DiluterTimer.Stop();
        //    if (PumpState == 0)
        //    {
        //        PumpState = 1;//只设置，不动作，下面再动作
        //    }
        //    else if (PumpState == 1)//在推进时触动这个事件，说明已经到头，需要后退
        //    {
        //        PumpState = -1;
        //        if (CycleNum > 0 && RwdCycleDur > 0)
        //        {
        //            DiluterTimer.Interval = RwdCycleDur;
        //        }
        //        if (CycleNum == 0 && LastFwdDur > 0)
        //        {
        //            DiluterTimer.Interval = LastFwdDur * Syringespd / 99.00;//最后一次后退不是全退
        //        }
        //        SendtoSerial("FF020126AC0255");
        //        DiluterTimer.Start();
        //    }
        //    else if (PumpState == -1)
        //    {
        //        if (CycleNum == 0)
        //        {
        //            PumpState = 0;
        //            //CycleNum = 0;
        //            //PartVol = 0;
        //            SendtoSerial("FF020103E80055");
        //            Ended = true;
        //            //stop pump immediately已经完成最后一个来回，停止
        //        }
        //        else
        //        {
        //            PumpState = 1;//还没完成所有来回，继续设置为推进
        //            CycleNum--;//一个来回减少一次循环次数，选择在后退到头时减少要完成的循环数
        //        }
        //    }

        //    if (PumpState == 1)
        //    {
        //        //send forward commands
        //        int spd = (int)Math.Round(Syringespd * 100);
        //        if (CycleNum > 0 && FwdCycleDur > 0)
        //        {
        //            DiluterTimer.Interval = FwdCycleDur;
        //        }
        //        if (CycleNum == 0 && LastFwdDur > 0)
        //        {
        //            DiluterTimer.Interval = LastFwdDur;
        //        }
        //        SendtoSerial("FF0201" + spd.ToString("X4") + "0155");
        //        DiluterTimer.Start();
        //    }
        //    //调试排气错误时留下的记录，因为排气时临时把针筒速度调成最大，而周期时间没有随之改变，造成错误。
        //    //SharedComponents.LogMsg += "\r\nTimer Interval:" + DiluterTimer.Interval.ToString() + "\r\nfwdCycleDuration:" + FwdCycleDur.ToString();
        //}

        public double GetRemainingVol()
        {
            double volume = 0;
            if(infusing)
            {
                //如果正在注射，返回剩余注射量
                TimeSpan elapsedtime;
                elapsedtime = DateTime.Now - starttime;
                double fraction = elapsedtime.TotalSeconds / GetDuration();
                volume = PartVol * (1 - fraction);
                //Console.WriteLine(Name + "时长：" + GetDuration().ToString());
                //Console.WriteLine(Name + "用时：" + elapsedtime.TotalSeconds);
                return volume;
            }
            else
            {
                //如果没有正在注射，返回剩余体积
                if (infused)
                    //如果已经注射完成，返回0
                    return 0;
                else
                    return PartVol;
            }
        }

        public bool isInfusing()
        {
            return infusing;
        }

        public bool hasInfused()
        {
            return infused;
        }

        public double GetInfusedVol()
        {
            return PartVol - GetRemainingVol();
        }

        public string GetTestMsg()
        {
            string strstate = "停止";
            //if (PumpState == 1)
            //    strstate = "推进";
            //if (PumpState == -1)
            //    strstate = "后退";
            double remainingvol = GetRemainingVol();
            TestMsg = DateTime.Now + strstate + "剩余体积：" + remainingvol.ToString("F3");
            TestMsg += "starttime:" + starttime;
            return TestMsg;
        }

        //public static byte[] StringToByteArray(string hex)
        //{
        //    return Enumerable.Range(0, hex.Length)
        //                     .Where(x => x % 2 == 0)
        //                     .Select(x => Convert.ToByte(hex.Substring(x, 2), 16))
        //                     .ToArray();
        //}

        //private void SendtoSerial(string msg)
        //{
        //    byte[] outputByte = StringToByteArray(msg);
        //    if (serialPort != null && serialPort.IsOpen)
        //        serialPort.Write(outputByte, 0, 7);
        //}

        //以下是旧代码，暂时保留，等新代码稳定后删除，主要是提前计算好推拉的行程和次数
        //public void SetVol(double volume)
        //{
        //    PartVol = volume;
        //    double totalLen = PartVol / Math.PI / SyringeDia / SyringeDia * 4000;//mm
        //    TotalFwdDur = totalLen / Syringespd * 60 * 1000; //milliseconds
        //    if (totalLen <= CycleLen)
        //    {
        //        TotalCycleNum = 0;
        //        CycleNum = 0;
        //        LastFwdDur = TotalFwdDur;

        //    }
        //    else if (totalLen > CycleLen)
        //    {
        //        TotalCycleNum = Convert.ToInt32(Math.Floor(totalLen / CycleLen));
        //        CycleNum = TotalCycleNum;
        //        LastFwdDur = (totalLen - TotalCycleNum * CycleLen) / Syringespd * 60 * 1000;
        //    }
        //    //调试排气错误时留下的记录，因为排气时临时把针筒速度调成最大，而周期时间没有随之改变，造成错误。
        //    //SharedComponents.LogMsg += "\r\nTotalLen" + totalLen.ToString() + "\tlastfwdDur" + LastFwdDur.ToString() + "\tcycleL" + CycleLen.ToString();
        //    //SharedComponents.LogMsg += "\r\nfwdcycleDur" + FwdCycleDur.ToString();
        //}

        public void Initialize(LIB.ChannelSettings ch)
        {
            Controller = LIB.RS485Driver;
            Name = ch.ChannelName; //通道名称
            Address = ch.Address; //RS485地址
            tubeInnerDiameter = ch.TubeInnerDiameter; //mm
            wheelDiameter = ch.WheelDiameter; //mm
            divpermL = ch.DivpermL; //每毫升液体需要多少个编码值（一圈是16384）
            speed = ch.PumpSpeed; //转速，单位rpm
            HighConc = ch.HighConc; //mol/L
            //LowConc = 0; //mol/L
            TotalVol = 100.0; //mL
            ChannelColor = ch.ChannelColor;
            infused = false;
            infusing = false;
            //以下为旧代码，暂时保留，等新代码稳定后删除
            /*
            Port = ch.PortName;
            Name = ch.ChannelName;
            SyringeDia = ch.SyringeDiameter; //mm
            Syringespd = ch.SyringeSpeed; //mm/min
            CycleLen = ch.CycleLen; //mm
            PartVol = 0.0; //mL
            CycleNum = 0;
            TotalCycleNum = 0;
            LastFwdDur = 0;
            //FwdCycleDur = CycleLen / Syringespd * 60 * 1000;
            RwdCycleDur = CycleLen / 99 * 60 * 1000;
            if (serialPort == null)
            {
                if (LIB.AvailablePorts.Contains(Port))
                {
                    serialPort = new SerialPort
                    {
                        PortName = Port,
                        BaudRate = 9600,
                        DataBits = 8,
                        StopBits = StopBits.One,
                        Parity = Parity.None,
                        ReadTimeout = 500,
                        WriteTimeout = 500,
                    };
                }
            }
            if (serialPort != null)
            {
                //RS485控制板的问题？断电后重插第一次打开串口时通信丢信息，必须第二次打开才正常
                if (serialPort.IsOpen)
                    serialPort.Close();
                try
                {
                    serialPort.Open();
                }
                catch (UnauthorizedAccessException e)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"], LIB.NamedStrings["PrepSol"] + LIB.NamedStrings["PortOccupied"]);
                }
            }*/
        }

        /*/// <summary>应在总程序里面关闭串口</summary>
        public void ClosePort()
        {
            if (serialPort != null && serialPort.IsOpen)
                serialPort.Close();
        }*

        /*******************************************************************************
         * 以下是手动模式下测试用的指令，暂时保留，等新代码稳定后删除
         * 这些指令在手动模式下调用，主要是测试用的，实际配液时不需要调用。
         * 这些指令在手动模式下调用，主要是测试用的，实际配液时不需要调用。
        /// <summary>
        /// ////////////////////////////////////////////////////    
        /// </summary>
        //以下是在手动模式下测试用的指令，只在manual.cs中调用过。
        //public void Stop()
        //{
        //    SendtoSerial("FF020103E80055");
        //}

        //public void Forward(int speed)
        //{
        //    SendtoSerial("FF0201" + speed.ToString("X4") + "0155");
        //}

        //public void Rewind(int speed)
        //{
        //    SendtoSerial("FF0201" + speed.ToString("X4") + "0255");
        //}

        //public void FastForward()
        //{
        //    SendtoSerial("FF020126AC0155");
        //}

        //public void FastRewind()
        //{
        //    SendtoSerial("FF020126AC0255");
        //}

        //public void SendCommand(string cmd)
        //{
        //    //TODO:增加校验代码，只能发送有效指令
        //    SendtoSerial(cmd);
        //}
         *******************************************************************************/

    }
}
