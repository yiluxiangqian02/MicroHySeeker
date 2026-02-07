using System;
using System.Collections.Generic;
using System.IO.Ports;
using System.Linq;
using System.Timers;
//RS485步进电机驱动程序
//所有电机都在一个总线上，因此一个实例负责一个COM口上所有电机，通过指定地址分别控制电机，地址0为广播地址
//调用程序创建电机实例后，需要指定串口，
//如需读取电机的与串口的通信数据，可以处理SerialCommunication事件，也可以不处理
//读取电机数据时需声明代管函数，并将回调函数指定为代管函数，然后将代管函数作为一个参数传递给ReadSettings方法
//例子：
//      声明和实例化电机控制器，并指定COM端口和初始化完成回调函数（可以为null）
//      MotorsOnRS485 RS485Controller;
//      RS485Controller = new MotorsOnRS485();
//      RS485Controller.Initialize(Serialport,ReadAllSettingsCallback);
//
//      地址为1的电机以20 rpm的速度正向转动
//      RS485Controller.CWRun(20, 1);
//
//      地址为1的电机以20 rpm的速度反向转动
//      RS485Controller.CCWRun(20, 1);
//
//      地址为1的电机停止
//      RS485Controller.Stop(1);
//
//      读取地址为1的电机参数
//      RS485Controller.ReadSettings(1,SettingsCallback);
//
//      SettingsCallback的定义如下（ShowMotorSettings为自定义函数，无参数，无返回值）：
//      DelegateReadSettings SettingsCallback = ShowMotorSettings;
//
//      ReadMotorSettings托管函数的声明是全局的，放在类定义之外
//      public delegate void DelegateReadSettings();
//
//      处理电机和COM口之间的通信，处理SerialCommunication事件
//      RS485Controller.SerialCommunication += Motor_SerialCommunication;
//            
//      事件的参数，是读或者写，以及具体数据
//private void Motor_SerialCommunication(object sender, MotorsOnRS485.SerialCommunicationEventArgs e)
//{
//    if (e.Operation == MotorsOnRS485.SerialCommType.read)
//        SetMsgbox(e.Data, " 接收 ");
//    if (e.Operation == MotorsOnRS485.SerialCommType.write)
//        SetMsgbox(e.Data, " 发送 ");

//}
namespace eChemSDL
{
    //一个模块管理一个串口上的所有马达
    public partial class MotorsOnRS485
    {
        //串口由调用程序统一管理，在接收到数据时必须调用ReceivedFeedback方法来反馈

        private SerialPort serialPort; //= new SerialPort();
        public string Port { get; set; }
        public List<string> CommandBuffer = new List<string>();//命令缓冲也是所有马达共享的
        public string DelayedHeader = ""; //有时串口返回信息会断开，这里保存断开后跨事件的信息头
        public List<MotorDefinition> MotorList = new List<MotorDefinition>();//只能自动保存连续编号的马达
        private int CheckMotorAddr; //检查马达参数时的地址
        public bool MotorsOnline { get; set; }
        public MotorDefinition MotorParamTsf = new MotorDefinition();//用作数据转移用

        private Timer SerialTimeout; //串口读取超时，探测有多少个马达在线，发地址不再有反应时，说明达到了最后一个马达，如果是写超时，说明掉线
 

        //调用读取电机参数时的回调函数地址，因为要等待串口，用这个私有成员来保存回调函数地址
        private DelegateReadSettings ReadSettingsCallback;//全部马达的参数
        private DelegateReadSettings ReadNextMotorCallback;//一个马达的参数，必须要设置两个函数指针，否则Initialize里面确定外部对象的回调函数在ReadSettings里面就被覆盖了

        public enum MotorStatus
        {
            stopped,
            running
        }
        public enum MotorDirection
        {
            forward,
            reverse
        }
        public enum SerialCommType
        {
            read,
            write
        }

        //这里的MotorDefinition是硬件相关的，和主程序里的马达参数不重复，后者主要是定义功能。
        public class MotorDefinition
        {
            public int Address { get; set; }
            public MotorStatus Status { get; set; }
            public MotorDirection Direction { get; set; }
            public int Rpm { get; set; }
            public int MaxRpm { get; set; }

            public MotorDefinition()
            {
                Address = 1;
                Status = MotorStatus.stopped;
                Direction = MotorDirection.forward;
                Rpm = 0;
                MaxRpm = 0;
            }

            public MotorDefinition(MotorDefinition md)
            {
                Address = md.Address;
                Status = md.Status;
                Direction = md.Direction;
                Rpm = md.Rpm;
                MaxRpm = md.MaxRpm;
            }

        }

        public void DetachDataReader()
        {
            if (serialPort != null)
            {
                serialPort.DataReceived -= SerialDataReceiver;
                serialPort.Close();
            }
        }


        //处理从设备返回来的数据，如果是写寄存器，设备会把同样的命令返回，如果命令缓冲区还有未执行的命令，则送出；
        //如果是读寄存器，设备会返回寄存器数据，处理显示。
        //这里只是处理数据，不是回调
        public void ProcessFeedback(string msg)
        {
            if (msg.Length >= 16)//读参数返回最少的位数是16位
            {
                SerialTimeout.Stop();//确实读到数据解析了，才停止倒计时
                string msgNoCRC;
                //减去CRC码
                msgNoCRC = msg.Substring(0, msg.Length - 4);
                //如果只是写寄存器命令确认返回，不需要做任何操作，直接执行下一条指令（如果有的话）。
                if (msgNoCRC[3] == '6')
                {
                    if (CommandBuffer.Count > 0)
                    {
                        if(msgNoCRC.Equals(CommandBuffer[0]))
                            CommandBuffer.RemoveAt(0);
                        if (CommandBuffer.Count > 0)
                            SendtoSerial(CommandBuffer[0]);
                    }
                    if (CommandBuffer.Count == 0)
                        UpdateMotorList();
                }
                //如果是读寄存器命令返回的返回数据，则把数据存入缓冲，并执行下一条直至完成，完成后调用ParseSettings解析数据
                else if (msgNoCRC[3] == '3')
                {
                    FillMotorParam(msgNoCRC);
                    if (CommandBuffer.Count > 0)
                        CommandBuffer.RemoveAt(0);
                    ReadNextMotorCallback();
                }
            }
            //if (CommandBuffer.Count > 0)
            //    SendtoSerial(CommandBuffer[0]);//除非缓冲区是空的，否则只在应答后才发送指令
        }

        //
        public void FillMotorParam(string motorinfo)
        {
            //TODO:这里会变成四个马达，怎么回事呢？
            MotorsOnline = true;
            if (motorinfo.Length >= 36)
            {
                if (motorinfo[11] == '1')
                    MotorParamTsf.Status = MotorStatus.running;
                else if (motorinfo[11] == '0')
                    MotorParamTsf.Status = MotorStatus.stopped;
                if (motorinfo[15] == '1')
                    MotorParamTsf.Direction = MotorDirection.forward;
                else if (motorinfo[15] == '0')
                    MotorParamTsf.Direction = MotorDirection.reverse;

                //速度计算
                MotorParamTsf.Rpm = Convert.ToInt16(motorinfo.Substring(16, 4), 16) / 10;

                //地址计算
                MotorParamTsf.Address = Convert.ToInt16(motorinfo.Substring(20, 4), 16);

                //最大速度计算
                MotorParamTsf.MaxRpm = Convert.ToInt16(motorinfo.Substring(32, 4), 16) / 10;
            }
            //0303 0007 0000 0001 00C8 0003 2580 0001 03E8 
            //指令 长度 运行 方向 速度 地址 波特 未知 限速
            if (MotorList.Count == 0)
                MotorList.Add(new MotorDefinition(MotorParamTsf));
            else
            {
                MotorDefinition existmotor = MotorList.FirstOrDefault(md => md.Address == MotorParamTsf.Address);
                if (existmotor != null)
                {
                    existmotor.Direction = MotorParamTsf.Direction;
                    existmotor.Status = MotorParamTsf.Status;
                    existmotor.Rpm = MotorParamTsf.Rpm;
                    existmotor.MaxRpm = MotorParamTsf.MaxRpm;
                }
                else
                    MotorList.Add(new MotorDefinition(MotorParamTsf));
            }
        }


        public void Run(float rpm, bool CW, int address)
        {
            string direction;
            //广播命令只能设置启动，连续发多个命令从机没反应
            //每个运行需要依次发3条指令，所以需要缓冲
            if (address == 0)
            {
                if (CommandBuffer.Count == 0)
                    SendtoSerial("000600000001");
                else
                    BufferCommand("000600000001");
            }
                
            else if (address < 255)
            {
                if (CW == true)
                    direction = "0600010001";
                else
                    direction = "0600010000";
                string RPM;
                //CommandBuffer.Clear();
                //MotorParamTsf.Address = address;
                RPM = (Convert.ToInt16(rpm * 10)).ToString("X4");
                if (CommandBuffer.Count == 0)
                    SendtoSerial(address.ToString("X2") + "060002" + RPM);
                else
                    BufferCommand(address.ToString("X2") + "060002" + RPM);//设置速度
                BufferCommand(address.ToString("X2") + direction);//设置转向
                BufferCommand(address.ToString("X2") + "0600000001");//设置启动
            }
        }

        public bool CWRun(float rpm, int address)
        {
            //if (CommandBuffer.Count > 0)
            //    return false;
            Run(rpm, true, address);
            return true;
        }

        public bool CCWRun(float rpm, int address)
        {
            //if (CommandBuffer.Count > 0)
            //    return false;
            Run(rpm, false, address);
            return true;
        }

        public void BufferCommand(string cmd)
        {
            if (CommandBuffer.Count < 20)
                CommandBuffer.Add(cmd);
            else
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["NoConnection"]);
        }

        public bool Stop(int address)
        {
            string command;
            //if (address != 0 && address < 255)
            //    MotorParamTsf.Address = address;
            command = address.ToString("X2") + "0600000000";
            if (CommandBuffer.Count == 0)
                SendtoSerial(command); //如果命令缓冲区已清空，需要主动发送指令已触发设备
            else
                BufferCommand(command);//如果命令缓冲区里还有命令，直接添加进去队列就可以，可以触发设备返回，继续执行完所有指令
            return true;
        }

        public bool ChangeAddress(int address)
        {
            if (address > 0 && address < 255)
            {
                string command;
                command = CheckMotorAddr.ToString("X2") + "06000300" + address.ToString("X2");
                if (CommandBuffer.Count == 0)
                    SendtoSerial(command);
                else
                    BufferCommand(command);
                CheckMotorAddr = address;
            }
            return true;
        }

        private void SerialDataReceiver(object sender, SerialDataReceivedEventArgs e)
        {
            //每次有数据进来就会触发，然后调用ProcessFeedback函数来处理，同时把信息作为事件参数触发事件，可供调用者查询
            string feedback="";
            string header="";
            SerialPort sp = (SerialPort)sender;
            //在这里注意的是，必须用一个变量保留BytesToRead的值，因为每读一次串口BytesToRead经常会改变的
            int datalength = sp.BytesToRead;
            try
            {
                if (datalength >= 4)//先通过前四个字节判断信息类型和长度，确定信息是否完整,如果数据没有超过4个字节，先不读，但下次读的时候需要断句，有可能包含两条信息
                {
                    if (string.IsNullOrEmpty(DelayedHeader))
                    {
                        byte[] headerByte = new byte[4];
                        //网上说有时串口会触发两次，但其中有一次没有数据，这里不受影响，因为没有数据也不会读的。
                        if (sp.Read(headerByte, 0, 4) == 4)
                        {
                            header = BitConverter.ToString(headerByte).Replace("-", string.Empty);
                            DelayedHeader = "";
                        }
                        else
                            LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["FlushPumpComError"]);

                    }
                    else
                        header = LIB.Clone(DelayedHeader);
                    if (header[3] == '6')
                    {
                        if (datalength >= 8)
                        {
                            byte[] dataByte = new byte[4];
                            if (sp.Read(dataByte, 0, 4) == 4)
                            {
                                feedback = header + BitConverter.ToString(dataByte).Replace("-", string.Empty);
                                ProcessFeedback(feedback);
                            }
                            else
                                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["FlushPumpComError"]);
                        }
                        else//如果剩下的信息不完整，只能等完整了再读，先保存前面的信息头
                            DelayedHeader = header;
                    }
                    else if (header[3] == '3')
                    {
                        int availabledatalength = Convert.ToInt32(header.Substring(4, 4)) * 2;
                        if (datalength >= (4 + availabledatalength + 2))
                        {
                            byte[] dataByte = new byte[availabledatalength + 2];
                            if (sp.Read(dataByte, 0, availabledatalength + 2) == availabledatalength + 2)
                            {
                                feedback = header + BitConverter.ToString(dataByte).Replace("-", string.Empty);
                                ProcessFeedback(feedback);
                            }
                            else
                                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["FlushPumpComError"]);
                        }
                        else//如果剩下的信息不完整，只能等完整了再读，先保存前面的信息头
                            DelayedHeader = header;
                    }
                    //下面的语句只是负责把串口返回的数据作为事件传送回调用者，不影响命令执行情况。
                    SerialCommunicationEventArgs args = new SerialCommunicationEventArgs();
                    args.Data = feedback;
                    args.Operation = SerialCommType.read;
                    OnSerialCommunication(args);
                }

            }
            catch (TimeoutException)
            {
                SerialCommunicationEventArgs args = new SerialCommunicationEventArgs();
                args.Data = "读取超时";
                args.Operation = SerialCommType.read;
                OnSerialCommunication(args);
            }
        }

        //调用者必须调用这个函数绑定串口，在里面添加了当接收到数据时的处理函数。
        public void Initialize(DelegateReadSettings callback)
        {
            ReadSettingsCallback = callback;//这个函数主要是为了通知调用程序初始化完成，可以读取全部马达参数了
            CommandBuffer.Clear();
            SerialTimeout = new Timer(500);//假设500毫秒内必有应答
            SerialTimeout.AutoReset = false;
            SerialTimeout.Elapsed += SerialTimeout_Elapsed;
            MotorsOnline = false;

            if(serialPort == null)
            {
                string portName;
                portName = Properties.Settings.Default.Flusher485Port;
                if (LIB.AvailablePorts.Contains(portName))
                {
                    serialPort = new SerialPort
                    {
                        PortName = portName,
                        //BaudRate = 9600,
                        BaudRate = 38400, //RS485电机的波特率
                        DataBits = 8,
                        StopBits = StopBits.Two,
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
                    serialPort.DataReceived += new SerialDataReceivedEventHandler(SerialDataReceiver);
                    //自检过程探测在线所有马达，填充MotorList
                    UpdateMotorList();
                }
                catch(UnauthorizedAccessException)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"], LIB.NamedStrings["Flush"] + LIB.NamedStrings["PortOccupied"]);
                }
            }
        }

        private void SerialTimeout_Elapsed(object sender, ElapsedEventArgs e)
        {
            if (CommandBuffer.Count > 0)
            {
                if (CommandBuffer[0][3] == '3')
                {
                    //读取失败，记为读取完成
                    CommandBuffer.RemoveAt(0);
                    ReadSettingsCallback?.Invoke();
                    if (CommandBuffer.Count > 0)
                        SendtoSerial(CommandBuffer[0]);

                }
                else if (CommandBuffer[0][3] == '6')
                //写入失败，记为掉线
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["FlushPumpComError"]);
                    MotorsOnline = false;
                }
                else
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["IllegalCommand"]);
                    MotorsOnline = false;
                }
            }
            else
            {
                MotorsOnline = false;
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["FlushPumpComError"]);
            }
        }

        //这个可以直接调用
        public void ReadSettings(int address, DelegateReadSettings callback)
        {
            if (address == 0)
                address = 1;//不能通过广播地址读设置

            //把回调函数先保存在私有成员中,如果只需链式查询，可以不这么做，直接在接收消息后调用CheckNextMotor就可以了
            //保留这个回调函数的目的是为外部对象提供单独查询某个马达的可能
            ReadNextMotorCallback = callback;
            //CommandBuffer.Clear();

            //这里只负责输出读寄存器指令，接下来要去接收串口信息那里等消息；
            BufferCommand(address.ToString("X2") + "0300000007");//可以一次读7个寄存器的数据
            SendtoSerial(CommandBuffer[0]);
        }

        public void UpdateMotorList()
        {
            CheckMotorAddr = 1;
            ReadSettings(CheckMotorAddr, CheckNextMotor);//启动读取的链式调用
        }

        private void CheckNextMotor()
        {
            if (CheckMotorAddr < 255)
                CheckMotorAddr++;
            ReadSettings(CheckMotorAddr, CheckNextMotor);
        }

        //public void RetrytilAbort(Object source, ElapsedEventArgs e)
        //{
        //    SerialTimeout.Stop();
        //    if (CommandBuffer.Count == 0)
        //        Retrytimes = 0;
        //    else if (Retrytimes < 2)
        //    {
        //        Retrytimes++;
        //        SendtoSerial(CommandBuffer[0]);
        //    }
        //    else
        //    {
        //        //CommandBuffer.Clear();//当前命令没执行超过三次就放弃当前命令
        //        CommandBuffer.RemoveAt(0);
        //        if (CommandBuffer.Count > 0)
        //            SendtoSerial(CommandBuffer[0]);
        //        Retrytimes = 0;
        //    }
        //}

        //发送单条命令
        public string SendtoSerial(String msg)
        {
            //防止奇数个数情况越界出错
            int msglength;
            if (msg.Length % 2 != 0)
                msglength = msg.Length / 2 + 1;
            else
                msglength = msg.Length / 2;
            byte[] cmdByte = new byte[msglength];
            byte[] outputByte = new byte[cmdByte.Length + 2];
            byte[] CRC = new byte[2];
            string command;
            SerialCommunicationEventArgs args = new SerialCommunicationEventArgs();

            cmdByte = StringToByteArray(msg);
            cmdByte.CopyTo(outputByte, 0);
            CRC = CalculateCRC(cmdByte);
            CRC.CopyTo(outputByte, cmdByte.Length);
            if (serialPort != null && serialPort.IsOpen)
                serialPort.Write(outputByte, 0, outputByte.Length);
            SerialTimeout.Start();//开始期待应答的倒计时

            //发送事件告诉调用者发送命令了。
            command = BitConverter.ToString(outputByte).Replace("-", string.Empty);
            args.Data = command;
            args.Operation = SerialCommType.write;
            OnSerialCommunication(args);
            return command;
        }

        public static byte[] StringToByteArray(string hex)
        {
            if ((hex.Length % 2) != 0)//防止奇数位出错
                hex = "0" + hex;
            return Enumerable.Range(0, hex.Length)
                             .Where(x => x % 2 == 0)
                             .Select(x => Convert.ToByte(hex.Substring(x, 2), 16))
                             .ToArray();
        }

        public static byte[] CalculateCRC(byte[] bufData)
        {
            ushort CRC = 0xFFFF;
            for (int i = 0; i < bufData.Length; i++)
            {
                CRC ^= bufData[i];
                for (int j = 0; j < 8; j++)
                {
                    if ((CRC & 0x0001) != 0)
                    {
                        CRC >>= 1;
                        CRC ^= 0xA001;
                    }
                    else
                    {
                        CRC >>= 1;
                    }
                }
            }
            return System.BitConverter.GetBytes(CRC);
        }

        protected virtual void OnSerialCommunication(SerialCommunicationEventArgs e)
        {
            EventHandler<SerialCommunicationEventArgs> handler = SerialCommunication;
            if (handler != null)
            {
                handler(this, e);
            }
        }

        public event EventHandler<SerialCommunicationEventArgs> SerialCommunication;

        public class SerialCommunicationEventArgs : EventArgs
        {
            public string Data { get; set; }
            public SerialCommType Operation { get; set; }
        }

        //用事件方式读取电机参数
        //protected virtual void OnSettingsReady(SettingsReadyEventArgs e)
        //{
        //    EventHandler<SettingsReadyEventArgs> handler = SettingsReady;
        //    if (handler != null)
        //    {
        //        handler(this, e);
        //    }
        //}

        //public event EventHandler<SettingsReadyEventArgs> SettingsReady;

        //public class SettingsReadyEventArgs : EventArgs
        //{
        //    public MotorStatus Status { get; set; }
        //    public MotorDirection Dir { get; set; }
        //    public int Address { get; set; }
        //    public int RPM { get; set; }
        //    public int MaxRPM { get; set; }
        //}
    }

    //声明代理函数SendText，感觉代理函数就像是在圈子外面的一个围观者，通过它可以临时取代任何一个圈子内的参数，防止循环调用的线程冲突。
    //这里定义两个代理函数类型，它们不是函数本身，函数本身是一个变量。
    //代理函数用法，首先，定义函数类型和参数表；其次，实例化，即用该函数类型声明一个变量，并将其指向一个普通函数；最后，用该函数类型的变量进行调用。
    public delegate void DelegateReadSettings();
}
