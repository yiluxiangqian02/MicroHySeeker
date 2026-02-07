using System;
using System.Collections.Generic;
using System.IO.Ports;
using System.Linq;
using System.Text;
using System.Timers;


namespace eChemSDL
{
    public class Positioner
    {
        //底层参数
        public string Port { get; set; }
        public int Speed { get; set; }
        public int PulsepercmX { get; set; }
        public int PulsepercmY { get; set; }
        public int PulsepercmZ { get; set; }
        public double cmperRow { get; set; }
        public double cmperCol { get; set; }
        public double cmperLay { get; set; }
        public int MaxRow { get; set; }
        public int MaxCol { get; set; }
        public int MaxLay { get; set; }
        public int Row { get; set; }
        public int Col { get; set; }
        public int Lay { get; set; }
        public int PickHeight { get; set; }//拾取的运行高度
        public int Index { get; set; }
        public bool Busy { get; set; }
        public bool Live { get; set; }//控制器有时会失去反应，需要停止实验
        public bool MsgSent { get; set; }//同一状态只发送一次消息
        public int QuiteTime { get; set; }//判断安静时间长度，单位为秒，超过这个时间需要发命令检查连接是否正常
        public int OfflineTime { get; set; }//判断掉线的时间间隔，单位为秒，超过这个时间认为设备掉线了

        protected DateTime LastTalk; //记录上次通讯的时间，设置Live变量，如果超过QuiteTime，可以认为掉线
        protected List<string> SendBuffer = new List<string>();//发送缓冲
        private SerialPort serialPort; //= new SerialPort();
        protected int targetRow;//保存目的地坐标，在平台到位后再更新平台的坐标为这些值
        protected int targetCol;
        protected int targetLay;
        //protected string ReadBuffer;
        protected byte[] ReadBuffer = new byte[0];//用字节数组当缓冲,避免出现汉字被中间截断,出现乱码
        protected bool Reading;


        private Timer CheckStatusTrigger;//计时器

        public enum SerialCommType
        {
            read,
            write
        }

        public Positioner()
        {
            //这个函数只有在第一次运行程序，没有保存设置时会被调用，这时串口还没有指定（肯定没有打开）
            Initialize();
        }


        public void Initialize()//
        {
            Speed = 20000;
            Row = 0;
            Col = 0;
            Lay = 0;
            Index = 0;
            MaxRow = 7;
            MaxCol = 7;
            MaxLay = 7;
            PickHeight = 1;
            PulsepercmX = 15000;
            PulsepercmY = 15000;
            PulsepercmZ = 15000;
            cmperRow = 1;
            cmperCol = 1;
            cmperLay = 1;
            QuiteTime = 2;
            OfflineTime = 10;
            CheckStatusTrigger = new Timer(50)//控制检查频度
            {
                AutoReset = false
            };
            CheckStatusTrigger.Elapsed += CheckStatus;
            CheckStatusTrigger.Enabled = false;
        }

        public void Connect()//连上平台，同步坐标数据？
        {
            LastTalk = DateTime.UtcNow;
            MsgSent = false;
            ReadyPort();
            UpdateStatus();
            SynctoHW();
        }

        public void SynctoHW()//同步是单向，只有从软件到硬件
        {
            ToPosition(Row, Col, Lay);
        }

        public void ReadyPort()
        {
            if (serialPort == null)
            {
                if (SerialPort.GetPortNames().Contains(Port))
                {
                    serialPort = new SerialPort
                    {
                        PortName = Port,
                        BaudRate = 115200,
                        DataBits = 8,
                        StopBits = StopBits.One,
                        Parity = Parity.None,

                        ReadTimeout = 500,
                        WriteTimeout = 500,
                        Encoding = Encoding.GetEncoding("GB2312")
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
                    serialPort.DataReceived += SerialDataReceiver;
                }
                catch (UnauthorizedAccessException)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"], LIB.NamedStrings["Positioner"] + LIB.NamedStrings["PortOccupied"]);
                }
            }
            targetRow = Row;
            targetCol = Col;
            targetLay = Lay;
        }
        //判断是否还有未执行的指令
        public bool Pending()
        {
            if (SendBuffer.Count > 0)
                return true;
            else
                return false;
        }
        public void DetachDataReader()
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.DataReceived -= SerialDataReceiver;
                serialPort.Close();
            }
        }

        public void CheckStatus(Object source, ElapsedEventArgs e)
        {
            //SendCommand("CJXSA");//状态轮询指令不走动作指令的通道，需要一直畅通，不能排队，因此不能直接调用SendCommand
            SerialCommunicationEventArgs args = new SerialCommunicationEventArgs();
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.Write("CJXSA");
                //清除数据接收区，否则其他命令产生的应答接进来会影响数据。
                //ReadBuffer = "";
            }
            args.Data = "CJXSA";
            args.Operation = SerialCommType.write;
            OnSerialCommunication(args);
        }

        public void CheckLink()
        {
            int elapsedseconds;
            DateTime now = DateTime.UtcNow;
            elapsedseconds = (now - LastTalk).Seconds;
            if (Live && elapsedseconds > QuiteTime)
            {
                //一直连接的情况下，每隔QuiteTime就再检查一下
                UpdateStatus();
            }
            if (elapsedseconds > OfflineTime)
            {
                Live = false;
                if(!MsgSent)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["Positioner"] + LIB.NamedStrings["NoConnection"]);
                    MsgSent = true;
                }
            }
        }

        public void UpdateStatus()
        {
            CheckStatusTrigger.Start();
        }

        public void Next()
        {
            if (Row > MaxRow || Col > MaxCol || Lay > MaxLay)
            {
                ZeroAll();
                return;
            }
            if (Col < MaxCol)
                targetCol = Col + 1;
            else
            {
                targetCol = 0;
                if (Row < MaxRow)
                    targetRow = Row + 1;
                else
                {
                    targetRow = 0;
                    if (Lay < MaxLay)
                        targetLay = Lay + 1;
                    else
                    {
                        ZeroAll();
                        return;
                    }
                }
            }
            ToPosition(targetRow, targetCol, targetLay);
        }

        public void NextPickAndPlace()
        {
            if (Row > MaxRow || Col > MaxCol || Lay > MaxLay)
            {
                ZeroAll();
                return;
            }
            if (Col < MaxCol)
                targetCol = Col + 1;
            else
            {
                targetCol = 0;
                if (Row < MaxRow)
                    targetRow = Row + 1;
                else
                {
                    ZeroAll();
                    return;
                }
            }
            PickAndPlace(targetRow, targetCol, PickHeight);
        }

        public void ToPosition(int r,int c,int l)
        {
            if (r > MaxRow)
                targetRow = MaxRow;
            else if (r < 0)
                targetRow = 0;
            else
                targetRow = r;
            if (c > MaxCol)
                targetCol = MaxCol;
            else if (c < 0)
                targetCol = 0;
            else
                targetCol = c;
            if (l > MaxLay)
                targetLay = MaxLay;
            else if (l < 0)
                targetLay = 0;
            else
                targetLay = l;
            Movetocms(targetCol * cmperCol, targetRow * cmperRow, targetLay * cmperLay);
        }

        public void IncPosition(int incr,int incc,int incl)
        {
            int row = Row + incr;
            int col = Col + incc;
            int lay = Lay + incl;
            if (col > MaxCol)
            {
                col = col - MaxCol;
                row += 1;
            }
            if (row > MaxRow)
            {
                row = row - MaxRow;
                lay += 1;
            }
            if (lay > MaxLay)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.NamedStrings["OutOfRangeLong"]);
                return;
            }
            ToPosition(Row + incr, Col + incc, Lay + incl);
        }

        public void PositionByAxis(string axis, int unit)
        {
            if (axis.Equals("X"))
                MovetoPulse(axis, Convert.ToInt32(unit * cmperCol * PulsepercmX));
            if (axis.Equals("Y"))
                MovetoPulse(axis, Convert.ToInt32(unit * cmperRow * PulsepercmY));
            if (axis.Equals("Z"))
                MovetoPulse(axis, Convert.ToInt32(unit * cmperLay * PulsepercmZ));
        }



        public void PickAndPlace(int r,int c, int l)//在2D阵列上进行拾取（Z轴起降）,l>0则先向上提，l<0则向下放
        {
            targetLay += l;
            if (l > MaxLay)
                targetLay = MaxLay;
            else if (l < 0)
                targetLay = 0;
            PositionByAxis("Z", targetLay);//只移动Z轴
            if (r > MaxRow)
                targetRow = MaxRow;
            else if (r < 0)
                targetRow = 0;
            if (c > MaxCol)
                targetCol = MaxCol;
            else if (c < 0)
                targetCol = 0;
            ToPosition(targetRow, targetCol, targetLay);//再移动X,Y轴
            targetLay -= l;//TODO:这个地方Lay立刻变为终值了，不会渐变，反正都要读状态，从状态里更新坐标好了，要注意计算精度问题。
            PositionByAxis("Z", targetLay);//再移动Z轴
        }


        public void Movetocms(double x, double y, double z)
        {
            int pulseX, pulseY, pulseZ;
            pulseX = Convert.ToInt32(x * PulsepercmX);
            pulseY = Convert.ToInt32(y * PulsepercmY);
            pulseZ = Convert.ToInt32(z * PulsepercmZ);
            MovetoPulse(pulseX, pulseY, pulseZ);
        }

        public void MovetoPulse(string axis, int pulse)//单轴移动指令
        {
            string str;
            //if (pulse < 0)
            //{
            //    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], "坐标为负值!");//可以为负值
            //    return;
            //}
            str = pulse.ToString();
            if (pulse >= 1000 || pulse <= -1000)
                str = str.Insert(str.Length - 3, ".");
            SendCommand($"CJXCg{axis}{str}F{Speed}$");
            Busy = true;//只要发送了移动命令都把状态设置为忙
            UpdateStatus();//每发一次指令后都要开始轮询装置是否还在运行中
        }

        public void MovetoPulse(int px,int py,int pz)
        {
            string strx, stry, strz;
            if (px < 0 || py < 0 || pz < 0)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], "坐标为负值!");
                return;
            }
            strx = (-px).ToString();
            stry = py.ToString();
            strz = (-pz).ToString();
            if (px >= 1000)
                strx = strx.Insert(strx.Length - 3, ".");
            if (py >= 1000)
                stry = stry.Insert(stry.Length - 3, ".");
            if (pz >= 1000)
                strz = strz.Insert(strz.Length - 3, ".");
            SendCommand($"CJXCgX{strx}Y{stry}Z{strz}F{Speed}$");
            Busy = true;//只要发送了移动命令都把状态设置为忙
            UpdateStatus();//每发一次指令后都要开始轮询装置是否还在运行中
        }

        public bool ZeroAll()
        {
            ZeroX();
            ZeroY();
            ZeroZ();

            return true;
        }

        public bool ZeroXY()
        {
            ZeroX();
            ZeroY();
            return true;
        }

        public bool ZeroX()
        {
            Row = 0;
            targetRow = 0;
            SendCommand("CJXZX");
            Busy = true;
            UpdateStatus();//每发一次指令后都要开始轮询装置是否还在运行中
            return true;
        }

        public bool ZeroY()
        {
            Col = 0;
            targetCol = Col;
            SendCommand("CJXZY");
            Busy = true;
            UpdateStatus();//每发一次指令后都要开始轮询装置是否还在运行中
            return true;
        }

        public bool ZeroZ()
        {
            Lay = 0;
            targetLay = Lay;
            SendCommand("CJXZZ");
            Busy = true;
            UpdateStatus();//每发一次指令后都要开始轮询装置是否还在运行中
            return true;
        }

        public void SendCommand(string cmd)
        {
            SerialCommunicationEventArgs args = new SerialCommunicationEventArgs();
            if (serialPort != null && serialPort.IsOpen)
            {
                if (!Busy)
                    serialPort.Write(cmd);
                else
                    SendBuffer.Add(cmd);
            }
            args.Data = cmd;
            args.Operation = SerialCommType.write;
            OnSerialCommunication(args);
        }

        private void SerialDataReceiver(object sender, SerialDataReceivedEventArgs e)
        {
            SerialPort sp = (SerialPort)sender;
            int datalength = sp.BytesToRead;
            try
            {
                if (datalength > 0)
                {
                    byte[] readbuffer = new byte[datalength];
                    //持续把所有数据读入,并追加到接收区ReadBuffer
                    sp.Read(readbuffer, 0, datalength);
                    byte[] temp = new byte[ReadBuffer.Length + datalength];
                    Buffer.BlockCopy(ReadBuffer, 0, temp, 0, ReadBuffer.Length);
                    Buffer.BlockCopy(readbuffer, 0, temp, ReadBuffer.Length, datalength);
                    ReadBuffer = temp;
                    //转化为string方便分析
                    string readstr= Encoding.GetEncoding("GB2312").GetString(ReadBuffer);
                    Live = true;//只要有应答，就设置为在线，否则就一直处于离线状态
                    LastTalk = DateTime.UtcNow;
                    int framestart = readstr.IndexOf("控制器");//先找到头部
                    if (framestart >= 0)
                    {
                        //掐去头部残余,前一次读取留下的东西
                        if (framestart > 0)
                        {
                            temp = new byte[ReadBuffer.Length - framestart];
                            Buffer.BlockCopy(ReadBuffer, framestart, temp, 0, ReadBuffer.Length - framestart);
                            ReadBuffer = temp;
                        }
                        int frameend = readstr.IndexOf("Out:", framestart);
                        //读到行尾
                        if (frameend >= 0)
                            frameend = readstr.IndexOf("\r\n", frameend);
                        int framelength = frameend - framestart;
                        if (framelength > 0)//确保找到了完整的一帧
                        {
                            Reading = false;
                            string frame = readstr.Substring(framestart, framelength);
                            if (frame.Contains("已停止"))
                            {
                                Busy = false;
                                string[] lines = frame.Split(new string[] { "\r\n" }, StringSplitOptions.RemoveEmptyEntries);
                                for (int i = 0; i < lines.Length; i++)
                                {
                                    if (lines[i].Contains("X:"))
                                        Col = (int)(-Convert.ToInt32(lines[i].Substring(2).Replace(".", "")) / PulsepercmX / cmperCol);
                                    if (lines[i].Contains("Y:"))
                                        Row = (int)(Convert.ToInt32(lines[i].Substring(2).Replace(".", "")) / PulsepercmY / cmperRow);
                                    if (lines[i].Contains("Z:"))
                                        Lay = (int)(-Convert.ToInt32(lines[i].Substring(2).Replace(".", "")) / PulsepercmZ / cmperLay);
                                }
                                if (SendBuffer.Count > 0)
                                {
                                    SendCommand(SendBuffer[0]);
                                    SendBuffer.RemoveAt(0);
                                    Busy = true;
                                    UpdateStatus();
                                }
                            }
                            if (frame.Contains("运行中"))
                            {
                                Busy = true;
                                if (!Reading)
                                    UpdateStatus();
                            }
                            SerialCommunicationEventArgs args = new SerialCommunicationEventArgs
                            {
                                Data = frame, //SerialResponse;
                                Operation = SerialCommType.read
                            };
                            OnSerialCommunication(args);
                            temp = new byte[ReadBuffer.Length - framelength];
                            Buffer.BlockCopy(ReadBuffer, framelength, temp, 0, ReadBuffer.Length - framelength);
                            ReadBuffer = temp;//只要有读到有效数据就清空接收区
                        }
                    }
                    else
                        Reading = true;
                }
            }
            catch (TimeoutException)
            {
                SerialCommunicationEventArgs args = new SerialCommunicationEventArgs
                {
                    Data = "读取超时",
                    Operation = SerialCommType.read
                };
                OnSerialCommunication(args);
            }
        }

        protected virtual void OnSerialCommunication(SerialCommunicationEventArgs e)
        {
            SerialCommunication?.Invoke(this, e);
        }

        public event EventHandler<SerialCommunicationEventArgs> SerialCommunication;

        public class SerialCommunicationEventArgs : EventArgs
        {
            public string Data { get; set; }
            public SerialCommType Operation { get; set; }
        }

    }
}
