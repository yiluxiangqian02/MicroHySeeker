using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Timers;
using System.Windows.Forms;



//定义ProgStep程序步骤；ExpProgram程序（ProgStep的列表）；Experiment实验
namespace eChemSDL
{
    public class Experiment
    {

        private System.Timers.Timer Clock;
        public ExpProgram Program;
        public List<ProgStep> ActiveSteps;
        public int CurrentStep { get; set; }
        public bool Running { get; set; }
        public bool ComboRunning { get; set; }
        public bool Interim { get; set; }//告诉调用者组合实验中发生了程序切换
        private DateTime StartTime;
        private DateTime ComboStartTime;
        public TimeSpan ElapsedTime { get; set; }
        public TimeSpan ElapsedStepTime { get; set; }
        public TimeSpan ElapsedComboTime { get; set; }
        public DateTime StepStart { get; set; }
        public double Duration { get; set; } //总长，单位：秒


        public Experiment()
        {
            Clock = new System.Timers.Timer();
            Clock.Elapsed += ClockTick;
            Clock.Interval = 1000;
            Clock.Start();
        }

        //这个函数不单单是估计运行时长，还要初始化很多关键（泵，注射器）变量
        public void PrepareSteps()
        {
            Duration = 0;
            LIB.VAPoints.Clear();
            LIB.VAPoints.Add(new PointF(0, 0));
            foreach (ProgStep ps in ActiveSteps)
            {
                //这里面已经放到ProgStep的PreptoExecute()方法中并统一将duration改为以秒为单位
                //if(ps.OperType == ProgStep.Operation.PrepSol)
                //{
                //    int matchingNum;
                //    double longeststepDuration = 0;
                //    //取配方和通道数中较小的一个，以免越界，通常两者是相等的。
                //    matchingNum = ps.Comps.Count <= SharedComponents.CHs.Count ? ps.Comps.Count : SharedComponents.CHs.Count;
                //    for (int i = 0; i < matchingNum; i++)
                //    {
                //        SharedComponents.Diluters[i].TotalVol = ps.TotalVol; //可能每一次配液的总体积不一样，在步骤内部设置溶液体积//必须在步骤执行时设置！在这里设置只是计算时间
                //        //这个函数只是计算步骤时间
                //        double thisstepduration = 0;
                //        SharedComponents.Diluters[i].SetConc(ps.Comps[i].LowConc);
                //        //这里必须设置了浓度才能计算步骤时间，所以这里也是必须的。在执行时用MakeConc间接调用了SetConc。
                //        thisstepduration = SharedComponents.Diluters[i].TotalFwdDur * (99 + SharedComponents.Diluters[i].Syringespd) / 99;
                //        if (thisstepduration > longeststepDuration)
                //            longeststepDuration = thisstepduration;
                //    }
                //    ps.Duration = longeststepDuration / 1000; //转换为秒
                //    ps.DurUnit = "sec";
                //    stepseconds = ps.Duration;
                //}
                //else if(ps.OperType == ProgStep.Operation.EChem)
                //{

                //}
                //else
                //{
                //    if (ps.DurUnit == "hr")
                //        stepseconds = ps.Duration * 3600;
                //    if (ps.DurUnit == "min")
                //        stepseconds = ps.Duration * 60;
                //    if (ps.DurUnit == "ms")
                //        stepseconds = ps.Duration / 1000;
                //    if (ps.DurUnit == "sec")
                //        stepseconds = ps.Duration;
                //    if(ps.OperType == ProgStep.Operation.Flush)
                //    {
                //        //重新调整冲洗时长为周期的整数倍
                //        int cycleDuration; //进出周期长之和
                //        int CycleNum;
                //        cycleDuration = SharedComponents.PPs[0].CycleDuration + SharedComponents.PPs[1].CycleDuration;
                //        if (ps.DurUnit == "cycle")
                //            CycleNum = Convert.ToInt32(ps.Duration);
                //        else
                //        {
                //            CycleNum = Convert.ToInt32(Math.Ceiling((stepseconds - SharedComponents.PPs[1].CycleDuration) / cycleDuration));//必须减去最后一次排出，否则循环数每次运行都增加
                //        }
                //        if (CycleNum < 0)
                //            CycleNum = 0;//不可以小于0
                //        stepseconds = cycleDuration * CycleNum + SharedComponents.PPs[1].CycleDuration;
                //        ps.Duration = stepseconds;
                //        ps.DurUnit = "sec";
                //        ps.FlushCycleNum = CycleNum;
                //        //不能只在实验程序初始化时初始化硬件，因为这样只能保留最后一步的数据，必须在执行时初始化硬件参数
                //        //比如第一次冲洗要10个循环，第二次5个循环，结果初始化完之后，两次都只有5个循环。
                //        SharedComponents.TheFlusher.Initialize();
                //        //SharedComponents.TheFlusher.SetCycle(CycleNum);
                //    }
                //}
                ps.PreptoExcute();
                Duration += ps.Duration;
            }
        }

        public void ResetStates()
        {

            if (ActiveSteps.Count > 0)
            {
                foreach (ProgStep ps in ActiveSteps)
                {
                    ps.State = ProgStep.StepState.idle;
                    ps.Started = false;
                }
            }

            for (int i = 0; i < LIB.Diluters.Count; i++)
            {
                LIB.Diluters[i].Initialize(LIB.CHs[i]);//每次开始新实验前必须初始化针筒！保险起见，为什么呢？因为有可能用户在configuration中更改了设置。
                                                                                 //每次新步骤时必须初始化针筒！！！因为一次实验可能要配很多次溶液！
            }
            LIB.TheFlusher.Initialize();
            LIB.CHI.CHIRunning = false;
            Running = false;
            CurrentStep = 0;
        }

        public void ResetComboStates()
        {
            ResetStates();
            ComboRunning = false;
        }

        public void LoadProgram(ExpProgram ep)
        {
            Program = ep;
            //program.InitializeCombo();//初始化组合参数会破坏现有数据
            ActiveSteps = Program.ParamCurValues;
            PrepareSteps();
        }

        public void RunProgram(bool freshStart)
        {
            if(!Running)
            {
                if (freshStart)
                {
                    ResetStates();
                    StartTime = DateTime.Now;
                    StepStart = StartTime;
                    CurrentStep = 0;
                    Running = true;//这个标志位是用来驱动定时器的，不能用于判断程序是否正在执行！因为在设置了这个标志位和程序实际开始执行之间有个时间差，在这段时间内如果访问程序变量，会出现错误！
                }
                LIB.ExpIDString = "EXPID. " + Program.ComboProgress().ToString("D4");
                //TODO:保留以后从断点继续实验的选项
            }
        }

        public void RunProgram(ExpProgram ep, bool freshStart)
        {
            LoadProgram(ep);
            RunProgram(true);
        }

        public void RunComboProgram(ExpProgram ep, bool freshStart)
        {
            Program = ep;
            if (Program.ComboParamsValid())
            {
                ComboRunning = true;
                ComboStartTime = DateTime.Now;
                ActiveSteps = Program.ParamCurValues;
                Program.LoadParamValues();
                RunComboProgram(freshStart);
            }
            else
                MessageBox.Show(LIB.NamedStrings["ComboNotValid"]);
        }

        public void RunComboProgram(bool freshStart)
        {
            //TODO:这个函数加入SkipList判断，不能在这里加！会停止在不运行的那个程序
            if (Program.SelectCombParams())//只有选中的程序才运行，否则最后一个程序总会运行
            {
                PrepareSteps();
                RunProgram(true);
            }
            else
            {
                if (Program.ComboCompleted())//保证在最后一个程序不运行时，关闭运行标志
                    ComboRunning = false;
            }
        }

        //定时器，驱动步骤执行，在这里主要是定时更新溶液的颜色和体积
        public void ClockTick(Object source, ElapsedEventArgs e)
        {
            LIB.PeriPumpSettings inletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Inlet");
            LIB.PeriPumpSettings outletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Outlet");
            LIB.PeriPumpSettings transferpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Transfer");

            if (Running)  //实验在运行中
            {
                ElapsedTime = DateTime.Now - StartTime;
                ElapsedStepTime = DateTime.Now - StepStart;
                ElapsedComboTime = DateTime.Now - ComboStartTime;
                if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.PrepSol)
                {
                    LIB.MixedSol.CurrentVol = 0;
                    double totalions = 0;
                    double dilution = 1;
                    double fraction = 0;
                    int r = 0, g = 0, b = 0, R = 0, G = 0, B = 0;
                    //设置混合溶液体积和颜色，先统计总共有多少离子
                    for (int i = 0; i < LIB.Diluters.Count; i++)
                    {
                        LIB.MixedSol.CurrentVol += LIB.Diluters[i].GetInfusedVol();
                        totalions += LIB.Diluters[i].GetInfusedVol() * LIB.Diluters[i].LowConc;
                    }
                    //再计算离子占的百分比
                    if (totalions > 0)
                    {
                        for (int i = 0; i < LIB.Diluters.Count; i++)
                        {
                            if (!ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                            { 
                            dilution = LIB.Diluters[i].GetInfusedVol() / LIB.MixedSol.CurrentVol;
                            r = (int)(LIB.Diluters[i].ChannelColor.R * dilution + 255 * (1 - dilution));
                            g = (int)(LIB.Diluters[i].ChannelColor.G * dilution + 255 * (1 - dilution));
                            b = (int)(LIB.Diluters[i].ChannelColor.B * dilution + 255 * (1 - dilution));
                            fraction = LIB.Diluters[i].GetInfusedVol() * LIB.Diluters[i].LowConc / totalions;
                            R += (int)(r * fraction);
                            G += (int)(g * fraction);
                            B += (int)(b * fraction); 
                            }
                        }
                    }
                    if (R > 255)
                        R = 255;
                    if (G > 255)
                        G = 255;
                    if (B > 255)
                        B = 255;//不知为何有时会出现越界的情况
                    //LIB.MixedSol.SolColor = Color.FromArgb(A, R, G, B);
                    LIB.MixedSol.SolColor = Color.FromArgb(255, R, G, B);
                    LIB.WorkingElectrolyte.SolColor = LIB.MixedSol.SolColor;
                }
                if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.Flush || ActiveSteps[CurrentStep].OperType == ProgStep.Operation.Transfer)
                {
                    if(LIB.TheFlusher.Bidirectional)
                    {
                        foreach(LIB.PeriPumpSettings pp in LIB.PPs)
                        {
                            if(pp.PumpStatus.IsRunning == true)
                            {
                                if(LIB.TheFlusher.CurrentDirection == LIB.PeriPumpSettings.PumpDirection.forward)
                                {
                                    LIB.MixedSol.CurrentVol -= (double)pp.PumpRPM / 30;
                                    if (LIB.MixedSol.CurrentVol < 0)
                                        LIB.MixedSol.CurrentVol = 0;
                                }
                                if (LIB.TheFlusher.CurrentDirection == LIB.PeriPumpSettings.PumpDirection.reverse)
                                {
                                    LIB.MixedSol.CurrentVol += (double)pp.PumpRPM / 30;
                                    if (LIB.MixedSol.CurrentVol > LIB.MixedSol.TotalVol)
                                        LIB.MixedSol.CurrentVol = LIB.MixedSol.TotalVol;
                                    LIB.MixedSol.SolColor = Color.Aqua;
                                    LIB.MixedSol.SoluteList.Clear();
                                }

                            }
                        }
                    }
                    else
                    {
                        if (inletpump.PumpStatus.IsRunning == true)
                        {
                            LIB.MixedSol.CurrentVol += ((double)LIB.PPs[0].PumpRPM / 30);
                            if (LIB.MixedSol.CurrentVol > LIB.MixedSol.TotalVol)
                                LIB.MixedSol.CurrentVol = LIB.MixedSol.TotalVol;
                            LIB.MixedSol.SolColor = Color.Aqua;
                            LIB.MixedSol.SoluteList.Clear();
                        }
                        if (outletpump.PumpStatus.IsRunning == true)
                        {
                            LIB.WorkingElectrolyte.CurrentVol -= ((double)outletpump.PumpRPM / 30);
                            if (LIB.WorkingElectrolyte.CurrentVol < 0)
                                LIB.WorkingElectrolyte.CurrentVol = 0;

                        }
                        if (transferpump.PumpStatus.IsRunning == true)
                        {
                            LIB.WorkingElectrolyte.SolColor = LIB.MixedSol.SolColor;
                            LIB.MixedSol.CurrentVol -= ((double)transferpump.PumpRPM / 30);//这个30是和蠕动泵的管径有关，以后可以设置
                            if (LIB.MixedSol.CurrentVol < 0)
                                LIB.MixedSol.CurrentVol = 0;
                            LIB.WorkingElectrolyte.CurrentVol += ((double)transferpump.PumpRPM / 30);//这个30是和蠕动泵的管径有关，以后可以设置
                            if (LIB.WorkingElectrolyte.CurrentVol > LIB.WorkingElectrolyte.TotalVol)
                                LIB.WorkingElectrolyte.CurrentVol = LIB.WorkingElectrolyte.TotalVol;
                        }
                    }
                }

                ProgStep.StepState stepState;
                stepState = ActiveSteps[CurrentStep].GetState(DateTime.Now - StepStart);

                //如果当前步骤未开始
                if (stepState == ProgStep.StepState.idle)
                {
                    StepStart = DateTime.Now;
                    ActiveSteps[CurrentStep].Started = true;
                    for (int i = 0; i < LIB.Diluters.Count; i++)
                    {
                        LIB.Diluters[i].Initialize(LIB.CHs[i]);//每次开始新实验前必须初始化针筒！保险起见，为什么呢？因为有可能用户在configuration中更改了设置。
                        //每次新步骤时必须初始化针筒！！！因为一次实验可能要配很多次溶液！
                        //但是在分批配液过程中不能初始化针筒，因为复位了泵的状态！
                    }
                    ExecuteStep();
                }
                else if (stepState.HasFlag(ProgStep.StepState.nextsol))
                    ExecuteStep(); //多步注入溶液重复调用
                else if (stepState == ProgStep.StepState.end)
                    CurrentStep++;
                if (CurrentStep >= ActiveSteps.Count)
                {
                    //CurrentStep = 0;
                    Running = false;
                    if (Program.ComboCompleted())
                        ComboRunning = false;
                    if (ComboRunning)
                    {
                        Program.NextComboParams();//这个保证移动到下一个实验
                        RunComboProgram(true);
                        Interim = true;
                    }
                }
            }
        }

        private void ExecuteStep()
        {
            if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.PrepSol)
            {
                //SharedComponents.MixedSol.CurrentVol = 0;
                LIB.MixedSol.TotalVol = ActiveSteps[CurrentStep].TotalVol;//每一步都设置溶液体积，可能每步不一样，不能在开始时统一设置
                int matchingNum;
                //取配方和通道数中较小的一个，以免越界，通常前者小于等于后者的。
                matchingNum = ActiveSteps[CurrentStep].Comps.Count <= LIB.CHs.Count ? ActiveSteps[CurrentStep].Comps.Count : LIB.CHs.Count;
                List<int> injectQueue = new List<int>(); //注入序号数组
                LIB.MixedSol.SoluteList.Clear();
                for (int i = 0; i < matchingNum; i++)
                {
                    LIB.Diluters[i].TotalVol = ActiveSteps[CurrentStep].TotalVol; //可能每一次配液的总体积不一样，在步骤内部设置溶液体积。
                    if (ActiveSteps[CurrentStep].Comps[i].LowConc > 0 || ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                    {
                        if(!ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                            LIB.MixedSol.SoluteList.Add(new SingleSolution(i, ActiveSteps[CurrentStep].Comps[i].LowConc, false));
                        if (!injectQueue.Contains(ActiveSteps[CurrentStep].Comps[i].InjectOrder) && !LIB.Diluters[i].hasInfused())//只有未完成的泵才加入
                            injectQueue.Add(ActiveSteps[CurrentStep].Comps[i].InjectOrder);
                    }
                }
                injectQueue.Sort();//从小到大排序
                LIB.WorkingElectrolyte = LIB.Clone(LIB.MixedSol);
                double solventvol = LIB.MixedSol.SolventVol();
                if (solventvol >= 0)
                {
                    //double stepDuration = 0;
                    for (int i = 0; i < matchingNum; i++)
                    {
                        if(ActiveSteps[CurrentStep].Comps[i].InjectOrder == injectQueue[0])
                        {
                            //if (ActiveSteps[CurrentStep].Comps[i].LowConc > 0.0 && !ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                            //{
                            //    //SharedComponents.Diluters[i].Initialize(SharedComponents.CHs[i]);//最好在步骤开始前就把针筒初始化好，见resetstate
                            //    LIB.Diluters[i].MakeConc(ActiveSteps[CurrentStep].Comps[i].LowConc);
                            //}
                            //if (ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                            //{
                            //    //SharedComponents.Diluters[i].Initialize(SharedComponents.CHs[i]);
                            //    LIB.Diluters[i].AddSolvent(solventvol);
                            //}
                            if (ActiveSteps[CurrentStep].Comps[i].LowConc > 0.0 || ActiveSteps[CurrentStep].Comps[i].IsSolvent)
                                LIB.Diluters[i].Infuse();//注入溶液，在此之前必须已经调用Prepare设置了浓度和体积
                        }
                    }
                }
                else
                {
                    ResetStates();
                    MessageBox.Show(LIB.NamedStrings["CannotMakeSol"]);// "很遗憾，这个溶液配不出来。。。");
                }
            }
            if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.Flush)
            {
                if(ActiveSteps[CurrentStep].EvacuateOnly)
                {
                    LIB.TheFlusher.SetCycle(0);
                    LIB.TheFlusher.Evacuate();
                }
                else
                {
                    LIB.TheFlusher.SetCycle(ActiveSteps[CurrentStep].FlushCycleNum);
                    LIB.TheFlusher.Flush();
                }
                //TODO:添加单泵冲洗
            }
            if(ActiveSteps[CurrentStep].OperType== ProgStep.Operation.Transfer)
            {
                ProgStep ps = ActiveSteps[CurrentStep];
                LIB.TheFlusher.SetCycle(0);
                LIB.TheFlusher.Transfer(ps.PumpAddress, ps.PumpRPM, ps.PumpDirection, ps.Duration);
            }
            if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.EChem)
            {
                LIB.CHI.RunExperiment(ActiveSteps[CurrentStep]);
                //TODO:保存前一步的溶液信息
            }
            if (ActiveSteps[CurrentStep].OperType == ProgStep.Operation.Change)
            {
                ProgStep ps = ActiveSteps[CurrentStep];
                LIB.ThePositioner.CheckLink();//检查连接
                if (ps.SimpleChange)
                {
                    if (ps.PickandPlace)
                        LIB.ThePositioner.NextPickAndPlace();
                    else
                        LIB.ThePositioner.Next();
                }
                else
                {
                    if (ps.PickandPlace)
                    {
                        LIB.ThePositioner.PositionByAxis("Z",LIB.ThePositioner.PickHeight);
                        LIB.ThePositioner.IncPosition(ps.IncY, ps.IncX, ps.IncZ);//先行后列，但X坐标是列坐标，Y坐标是行坐标。
                        LIB.ThePositioner.PositionByAxis("Z", -LIB.ThePositioner.PickHeight);
                    }
                    else
                    {
                        LIB.ThePositioner.IncPosition(ps.IncY, ps.IncX, ps.IncZ);//先行后列，但X坐标是列坐标，Y坐标是行坐标。
                    }
                }
            }
        }
    }
}
