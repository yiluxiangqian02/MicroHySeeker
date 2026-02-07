using System;
using System.IO.Ports;
using System.Linq;
using System.Timers;

namespace eChemSDL
{
    public class Flusher
    {
        private MotorRS485 Controller;
        private Timer InletTimer;
        private Timer OutletTimer;
        private Timer DelayTimer;//在连续发命令中间的间隔，防止设备不反应
        private Timer TrsfTimer; //移液时间
        private byte StopAddress; //暂时保存要停止的马达的地址
        public bool Bidirectional = false; //当有马达设为双向时，采用双向冲洗方式
        public LIB.PeriPumpSettings.PumpDirection CurrentDirection;//双向模式下记录运转方向
        public int CycleNumber = 0;

        public void Initialize()
        {
            //DelegateReadSettings SettingsReady = UpdateFlusherPumps;
            //SerialPort serialPort = LIB.SerialPorts.SingleOrDefault(sp => sp.PortName == LIB.FlusherCOMPort);
            //Controller.Initialize(serialPort, UpdateFlusherPumps);
            Controller = LIB.RS485Driver;
            //Controller.Initialize();//不在这里初始化，直接在主程序中初始化，因为Driver是公用的
            Bidirectional = false;
            InletTimer.Stop();
            OutletTimer.Stop();
            TrsfTimer.Stop();
            DelayTimer.Stop();
            //foreach (SharedComponents.PeriPumpSettings pp in SharedComponents.PPs)
            //{
            //    System.Timers.Timer DiluterTimer = new System.Timers.Timer();
            //    DiluterTimer.Interval = pp.CycleDuration * 1000;
            //    DiluterTimer.AutoReset = false;
            //    DiluterTimer.Enabled = false;
            //    DiluterTimer.Elapsed += Reverse;
            //    PumpTimers.Add(DiluterTimer, pp.Address);
            //}//以后再说吧，需要超过两个蠕动泵的时候再说
            //或者不管有多少个泵，只用两个计时器？或者说每一时间最多只能有两个泵在运行？
        }

        public void UpdateFlusherPumps()
        {
            // Update each configured pump's status by matching its address to the controller's motor list.
            foreach (var pp in LIB.PPs)
            {
                if (Controller.MotorList.ContainsKey(pp.Address))
                {
                    pp.PumpStatus = Controller.MotorList[pp.Address];
                }
                else
                {
                    // If not present, ensure PumpStatus reflects not running / unknown
                    pp.PumpStatus = new MotorRS485.MotorState { IsRunning = false };
                }
            }
        }

        public void Fill(Object source, ElapsedEventArgs e)
        {
            DelayTimer.Stop();
            DelayTimer.Elapsed -= Fill;
            InletTimer.Start();
            LIB.PeriPumpSettings inletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Inlet");
            //单泵模式
            //if (Bidirectional)
            //{
            //    for (int i = 0; i < SharedComponents.PPs.Count; i++)
            //    {
            //        if (SharedComponents.PPs[i].Direction == SharedComponents.PeriPumpSettings.PumpDirection.two_way)
            //        {
            //            RS485Controller.CCWRun(SharedComponents.PPs[i].PumpRPM, SharedComponents.PPs[i].Address);
            //            CurrentDirection = SharedComponents.PeriPumpSettings.PumpDirection.reverse;
            //            System.Threading.Thread.Sleep(50);
            //        }
            //    }
            //}
            //双泵模式
            if (!Bidirectional)
            {
                if (inletpump.Direction == LIB.PeriPumpSettings.PumpDirection.forward)
                    Controller.CWRun(inletpump.Address, inletpump.PumpRPM);
                if (inletpump.Direction == LIB.PeriPumpSettings.PumpDirection.reverse)
                    Controller.CCWRun(inletpump.Address, inletpump.PumpRPM);
                inletpump.PumpStatus.IsRunning = true;
            }
        }

        public void StopFill(Object source, ElapsedEventArgs e)
        {
            InletTimer.Stop();
            //if (CycleNumber > 0)
            //{
            //    CycleNumber--;
            //    Evacuate();
            //}
            ////双泵模式
            //if (!Bidirectional)
            //{
            //    StopAddress = 1;//注意马达地址是从1开始的，不是0
            //    DelayTimer.Start();
            //}
            //以下修改为三泵模式
            LIB.PeriPumpSettings inletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Inlet");

            Controller.Stop(inletpump.Address);
            inletpump.PumpStatus.IsRunning = false;
            DelayTimer.Elapsed += FlushTrsf;
            DelayTimer.Start();
        }

        //排空电解池
        public void Evacuate()
        {
            OutletTimer.Interval = LIB.PPs[1].CycleDuration * 1000;
            OutletTimer.Start();
            LIB.PeriPumpSettings outletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Outlet");


            if (CycleNumber > 0)
            {
                DelayTimer.Elapsed += Fill;//延迟启动注入泵
                DelayTimer.Start();
            }
            //在有两个烧杯时，使用了移液泵，就无法实现单泵清洗了，单泵清洗的入口和出口只用一条管子接入烧杯，在两个烧杯时不能实现
            //单泵，可同时启动多个设置双向的泵，只要启动了单泵就忽略双泵设置
            //for (int i = 0; i < 2; i++)
            //{
            //    if (SharedComponents.PPs[i].Direction == SharedComponents.PeriPumpSettings.PumpDirection.two_way)
            //    {
            //        RS485Controller.CWRun(SharedComponents.PPs[i].PumpRPM, SharedComponents.PPs[i].Address);
            //        SharedComponents.PPs[i].PumpStatus = MotorsOnRS485.MotorStatus.running;
            //        Bidirectional = true;
            //        CurrentDirection = SharedComponents.PeriPumpSettings.PumpDirection.forward;
            //        System.Threading.Thread.Sleep(50);
            //    }
            //}
            //双泵
            if (!Bidirectional)
            {
                if (outletpump.Direction == LIB.PeriPumpSettings.PumpDirection.forward)
                    Controller.CWRun(outletpump.Address, outletpump.PumpRPM);
                if (outletpump.Direction == LIB.PeriPumpSettings.PumpDirection.reverse)
                    Controller.CCWRun(outletpump.Address, outletpump.PumpRPM);
                outletpump.PumpStatus.IsRunning = true;
            }
        }

        public void FlushTrsf(Object source, ElapsedEventArgs e)
        {
            DelayTimer.Stop();
            DelayTimer.Elapsed -= FlushTrsf;
            LIB.PeriPumpSettings transfertpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Transfer");

            Transfer(transfertpump.Address, transfertpump.PumpRPM, transfertpump.Direction == LIB.PeriPumpSettings.PumpDirection.forward, transfertpump.CycleDuration);
        }

        //指定启动哪个泵进行移液，是否保持同样转速？同样方向？需要灵活性？
        public void Transfer(byte address, ushort rpm, bool direction, double runttime) 
        {
            TrsfTimer.Interval = runttime * 1000;
            TrsfTimer.Start();
            Controller.Run(address, rpm, direction);
            StopAddress = address;
            LIB.PPs.SingleOrDefault(pp => pp.Address == address).PumpStatus.IsRunning = true;
        }

        public void StartEvacuate(Object source, ElapsedEventArgs e)
        {
            DelayTimer.Elapsed -= StartEvacuate;
            Evacuate();//因为不能不带参数直接调用一个定时器的事件处理函数
        }

        public void StopTransfer(Object source, ElapsedEventArgs e)
        {
            TrsfTimer.Stop();
            Controller.Stop(StopAddress);
            LIB.PPs.SingleOrDefault(pp => pp.Address == StopAddress).PumpStatus.IsRunning = false;
            if (CycleNumber > 0)//注意：如果只执行移液操作，必须把CycleNumber置为0！
            {
                DelayTimer.Elapsed += StartEvacuate;
                DelayTimer.Start();
                CycleNumber--;
            }
        }

        public void StopEvacuate(Object source, ElapsedEventArgs e)
        {
            OutletTimer.Stop();
            //如果是最后一个周期，或者单独调用Evacuate，不再进行Fill//修改为三泵体系
            //
            //  Evacuate =(DelayTimer)=> Fill =====(InletTimer)=====> StopFill =(DelayTimer)=> Transfe r=====(TrsfTimer)=====> StopTransfer =(DelayTimer)=> Evacuate(重复)
            //           =====(OutletTimer)=====> StopEvacuate   
            //
            //
            //if (CycleNumber > 0)
            //    Fill();
            //单泵模式
            //else if (Bidirectional)
            //{
            //    StopAddress = 0;
            //    DelayTimer.Start();
            //}
            //双泵模式，停止排水泵和启动进水泵留出时间差，以免芯片通信堵塞
            //if (!Bidirectional)
            //{
            //    StopAddress = 2;
            //    DelayTimer.Start();
            //}
            LIB.PeriPumpSettings outletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Outlet");

            Controller.Stop(outletpump.Address);
            outletpump.PumpStatus.IsRunning = false;
        }

        public void StopMotor(Object source, ElapsedEventArgs e)
        {
            DelayTimer.Stop();
            Controller.Stop(StopAddress);
            if (StopAddress == 0)
                foreach (LIB.PeriPumpSettings pp in LIB.PPs)
                    pp.PumpStatus.IsRunning = false;
            else
                LIB.PPs[StopAddress - 1].PumpStatus.IsRunning = false;
        }

        public void SetCycle(int cycleNum)
        {
            CycleNumber = cycleNum;
        }

        public void Flush()
        {
            if (CycleNumber > 0)
                Evacuate();
        }


        public Flusher()
        {

            InletTimer = new Timer();
            OutletTimer = new Timer();
            DelayTimer = new Timer();
            TrsfTimer = new Timer();

            InletTimer.AutoReset = false;
            InletTimer.Enabled = false;
            InletTimer.Elapsed += StopFill;

            OutletTimer.AutoReset = false;
            OutletTimer.Enabled = false;
            OutletTimer.Elapsed += StopEvacuate;

            DelayTimer.Interval = 500;
            DelayTimer.AutoReset = false;
            DelayTimer.Enabled = false;
            //DelayTimer.Elapsed += StopMotor;

            TrsfTimer.AutoReset = false;
            TrsfTimer.Enabled = false;
            TrsfTimer.Elapsed += StopTransfer;

            Initialize();
        }
    }
}
