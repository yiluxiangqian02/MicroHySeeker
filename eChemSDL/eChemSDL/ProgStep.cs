using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;

namespace eChemSDL
{
    public class ProgStep
    {
        public enum Operation
        {
            [Description("空白")]
            Blank,
            [Description("配液")]
            PrepSol,
            [Description("电化学")]
            EChem,
            [Description("冲洗")]
            Flush,
            [Description("移液")]
            Transfer,
            [Description("换样")]
            Change
        };
        //public enum ECMode
        //{
        //    [Description("电流")]
        //    A,
        //    [Description("电压")]
        //    V
        //};//通用电化学设置
        //public enum ScanMode
        //{
        //    [Description("线性")]
        //    Linear,
        //    [Description("阶跃")]
        //    Step,
        //    [Description("脉冲")]
        //    Pulse
        //};
        //};//通用电化学设置

        public enum StepState
        {
            idle = 0,
            busy = 1,
            nextsol = 2,
            end = 4
        };//nextsol需要标记分步执行注液的状态，可以和busy同时

        public Operation OperType { get; set; }
        //public ECMode ECmode { get; set; }//通用电化学设置
        //public ScanMode scanMode { get; set; }//通用电化学设置
        public List<SingleSolution> Comps = new List<SingleSolution>();
        public double TotalVol { get; set; }
        public double TotalConc { get; set; }//组合实验时设置离子总浓度
        public bool ConstTotalConc { get; set; }
        public string CHITechnique { get; set; }
        public float E0 { get; set; }
        public float EH { get; set; }
        public float EL { get; set; }
        public float EF { get; set; }
        public float ScanRate { get; set; }
        public float Sensitivity { get; set; }
        public float AutoSensibility { get; set; }
        public float SamplingInterval { get; set; }
        public float ScanDir { get; set; }
        public float SegNum { get; set; }
        public float QuietTime { get; set; }
        public float RunTime { get; set; }

        public double Duration; //seconds，移液时也使用定时
        public string DurUnit { get; set; }
        public int FlushCycleNum { get; set; }//由于所有时长必须转换为秒钟，另外需要这个变量保存冲洗周期数，不用每次重复计算。
        public bool EvacuateOnly { get; set; }//设置只排空
        public bool PumpDirection { get; set; }
        public ushort PumpRPM { get; set; }
        public byte PumpAddress { get; set; }//设置用于排空和移液的泵地址

        public bool SimpleChange { get; set; }//简单换样，不单独控制每个轴
        public bool PickandPlace { get; set; }//带取放的换样方式
        public int IncX { get; set; }
        public int IncY { get; set; }
        public int IncZ { get; set; }//换样时单独控制轴

        public StepState State { get; set; }
        public bool Started { get; set; }

        public ProgStep()
        {
            State = StepState.idle;
            Started = false;
            //t1unit = "sec";
            //t2unit = "sec";
            DurUnit = "min";
            Duration = 1;
        }

        public string GetDesc()
        {
            string desc = "";
            if (OperType == Operation.PrepSol)
            {
                desc = "[" + LIB.NamedStrings["PrepSol"] + "]: "; //"[配液]:";
                string solvent = "";
                foreach (SingleSolution ss in Comps)
                {
                    if (!ss.IsSolvent)
                        desc += "[" + ss.Solute + "] = " + ss.LowConc.ToString() + ";";
                    else
                        solvent = ss.Solute;
                }
                if (!string.IsNullOrEmpty(solvent))
                    desc += LIB.NamedStrings["Solvent"] + " " + solvent;
            }
            if (OperType == Operation.EChem)
            {
                desc = "[" + LIB.NamedStrings["EChem"] + "]: ";//"[电化学]:";
                desc += CHITechnique;
                if (CHITechnique.Equals("CV"))
                {
                    if (ScanDir > 0.5)
                        desc += String.Format(" : {0} >> {1} >> {2} >> {3}(V)", E0, EH, EL, EF);
                    else
                        desc += String.Format(" : {0} >> {1} >> {2} >> {3}(V)", E0, EL, EH, EF);
                    desc += String.Format(" @ {0}(V/s) X {1}(Seg)", ScanRate, SegNum);

                }
                if (CHITechnique.Equals("LSV"))
                {
                    desc += String.Format(" : {0} >> {1}(V) @ {2}(V/s)", E0, EF, ScanRate);
                }
                if (CHITechnique.Equals("i-t"))
                {
                    desc += String.Format(" : @ {0}(V) X {1}(sec)", E0, RunTime);
                }
                //通用电化学（暂时不用）
                //if (ECmode == ECMode.A)
                //{
                //    desc += "电流";

                //}
                //if (ECmode == ECMode.V)
                //{
                //    desc += "电压";
                //}
                //if (scanMode == ScanMode.Linear)
                //    desc += "线性";
                //if (scanMode == ScanMode.Pulse)
                //    desc += "脉冲";
                //if (scanMode == ScanMode.Step)
                //    desc += "阶跃";
                //desc += "模式; 时间函数:";
                //desc += "(0," + EL.ToString() + "),(" + E0.ToString() + RunTime + "," + EF.ToString() + "),(" + EH.ToString() + t2unit + "," + ScanRate.ToString() + ")";
                //desc += "持续时间:" + Duration.ToString() + DurUnit;

            }
            if (OperType == Operation.Flush)
            {
                desc = "[" + LIB.NamedStrings["Flush"] + "]: ";  //"[冲洗]";
                desc += LIB.NamedStrings["Duration"] + ": " + Duration.ToString() + DurUnit;
            }
            if (OperType == Operation.Blank)
            {
                desc = "[" + LIB.NamedStrings["Blank"] + "]: ";  //"[空白]";
                desc += LIB.NamedStrings["Duration"] + ": " + Duration.ToString() + DurUnit;
            }

            if (OperType == Operation.Transfer)
            {
                desc = "[" + LIB.NamedStrings["Transfer"] + "]: ";  //"[移液]";
                desc += LIB.NamedStrings["PumpAddress"] + ": " + PumpAddress.ToString() + " ";
                desc += LIB.NamedStrings["Direction"] + ": " + (PumpDirection ? LIB.NamedStrings["forward"] : LIB.NamedStrings["reverse"]) + " ";
                desc += LIB.NamedStrings["Duration"] + ": " + Duration.ToString() + DurUnit;
            }

            if(OperType==Operation.Change)
            {
                desc = "[" + LIB.NamedStrings["Change"] + "]: ";  //"[换样]";
                if (SimpleChange)
                    desc += LIB.NamedStrings["Simple"];
                else
                {
                    desc += LIB.NamedStrings["Custom"] + ": ";
                    if (IncX!=0)
                        desc += "X" + LIB.NamedStrings["Move"] + IncX.ToString() + " ";
                    if (IncY != 0)
                        desc += "Y" + LIB.NamedStrings["Move"] + IncY.ToString() + " ";
                    if (IncZ != 0)
                        desc += "Z" + LIB.NamedStrings["Move"] + IncZ.ToString() + " ";
                }
                if (PickandPlace)
                    desc += $"({LIB.NamedStrings["PickandPlace"]})";
            }
            return desc;
        }
        public StepState GetState(TimeSpan elapsed)
        {
            //if (OperType == Operation.PrepSol)
            //{
            //    bool running = false;
            //    bool nextsol = false;
            //    for (int i = 0; i < SharedComponents.Diluters.Count; i++)
            //    {
            //        if (Comps[i].LowConc > 0 || Comps[i].IsSolvent)//有些泵是不参与步骤的，不能让它们的状态影响步骤状态的判断
            //        {
            //            if (SharedComponents.Diluters[i].PumpState != 0)//只要有泵在动，就是在运行中
            //                running = true;
            //            if (!SharedComponents.Diluters[i].Ended) //只有所有泵都跑完了才结束，不行，一开始所有泵都没跑完，必须设置为idle,不是running
            //                nextsol = true;//只要有一个泵没跑完，就还有下一批溶液，注意这个和上面的running不是互斥条件，可以同时
            //        }
            //    }
            //    if (running)//有泵在动
            //        State = StepState.busy;
            //    else //所有泵都不动
            //    {
            //        if (Started)
            //        {
            //            if (nextsol)
            //                State = StepState.busy | StepState.nextsol;
            //            else
            //                State = StepState.end;
            //        }
            //    }
            //}

            //else if (OperType == Operation.EChem)
            //{
            //    if (Started)
            //    {
            //        if (SharedComponents.CHI.CHIRunning)
            //            State = StepState.busy;
            //        else
            //            State = StepState.end;
            //    }
            //}

            //else if (Started)
            //{
            //    double stepseconds = Duration;
            //    if (DurUnit == "hr")
            //        stepseconds = Duration * 3600;
            //    else if (DurUnit == "min")
            //        stepseconds = Duration * 60;
            //    else if (DurUnit == "ms")
            //        stepseconds = Duration / 1000;

            //    if (elapsed.TotalSeconds > stepseconds)
            //        State = StepState.end;
            //    else
            //        State = StepState.busy;

            //}
            //else
            //    State = StepState.idle;
            //return State;
            //清晰逻辑，改为下面
            if(Started)
            {
                if (OperType == Operation.PrepSol)
                {
                    bool running = false;
                    bool nextsol = false;
                    for (int i = 0; i < LIB.Diluters.Count; i++)
                    {
                        if (Comps[i].LowConc > 0 || Comps[i].IsSolvent)//有些泵是不参与步骤的，不能让它们的状态影响步骤状态的判断，只统计实际参与配液的泵
                        {
                            if (LIB.Diluters[i].isInfusing())//只要有泵在动，就是在运行中
                                running = true;
                            if (!LIB.Diluters[i].hasInfused()) //只有所有泵都跑完了才结束，不行，一开始所有泵都没跑完，必须设置为idle,不是running
                                nextsol = true;//只要有一个泵没跑完，就还有下一批溶液，注意这个和上面的running不是互斥条件，可以同时
                        }
                    }
                    if (running)//有泵在动
                        State = StepState.busy;
                    else //所有泵都不动
                    {
                        if (nextsol)
                            State = StepState.busy | StepState.nextsol;
                        else
                            State = StepState.end;
                    }
                }
                else if (OperType == Operation.EChem)
                {
                    if (LIB.CHI.CHIRunning)
                        State = StepState.busy;
                    else
                        State = StepState.end;
                }
                else if(OperType==Operation.Change)
                {
                    //如果超时且1.要么不在线2.要么已经停止且没有待执行的命令
                    if (elapsed.TotalSeconds > Duration && (!LIB.ThePositioner.Live || !LIB.ThePositioner.Busy && !LIB.ThePositioner.Pending()))
                        State = StepState.end;
                    else
                        State = StepState.busy;
                }
                else
                {
                    double stepseconds = Duration;
                    if (DurUnit == "hr")
                        stepseconds = Duration * 3600;
                    else if (DurUnit == "min")
                        stepseconds = Duration * 60;
                    else if (DurUnit == "ms")
                        stepseconds = Duration / 1000;

                    if (elapsed.TotalSeconds > stepseconds)
                        State = StepState.end;
                    else
                        State = StepState.busy;

                }
            }
            else
                State = StepState.idle;
            return State;
        }

        public void PreptoExcute()
        {
            LIB.PeriPumpSettings inletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Inlet");
            LIB.PeriPumpSettings outletpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Outlet");
            LIB.PeriPumpSettings transferpump = LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Transfer");

            if (OperType == Operation.PrepSol)
            {
                int matchnum;
                double longeststepDuration = 0;
                LIB.MixedSol.CurrentVol = 0;
                LIB.MixedSol.TotalVol = TotalVol;
                LIB.MixedSol.SoluteList.Clear();

                //取配方和通道数中较小的一个，以免越界，通常两者是相等的。不对,一般来说配方要比通道数少,否则应该报错.//TODO:
                matchnum = Comps.Count <= LIB.CHs.Count ? Comps.Count : LIB.CHs.Count;
                List<int> injectQueue = new List<int>(); //注入序号数组
                List<double> maxDurations = new List<double>();//每个注入序号的最长时间
                //计算溶剂体积
                for (int i = 0; i < matchnum; i++)
                {
                    if (!Comps[i].IsSolvent)//不添加溶剂，虽然溶剂浓度设置为0时现在程序是同样忽略的，但万一用户把溶剂浓度设置为某个数呢？
                        LIB.MixedSol.SoluteList.Add(new SingleSolution(i, Comps[i].LowConc, false));
                    if (!injectQueue.Contains(Comps[i].InjectOrder))
                    {
                        injectQueue.Add(Comps[i].InjectOrder);
                        maxDurations.Add(0);
                    }
                }
                double solventvol = LIB.MixedSol.SolventVol();

                if (solventvol >= 0)
                {
                    for (int i = 0; i < matchnum; i++)
                    {
                        LIB.Diluters[i].TotalVol = TotalVol; //可能每一次配液的总体积不一样，在步骤内部设置溶液体积//必须在步骤执行时设置！在这里设置只是计算时间
                                                                          //这个函数只是计算步骤时间
                        double thisStepDuration = 0;
                        //以下注液时间计算必须在步骤执行时设置！在这里设置只是计算时间，旧代码，使用的电机不能定位模式运行，只能速度模式运行，所以只能通过运行时间来确定位置
                        //if (Comps[i].LowConc > 0.0 && !Comps[i].IsSolvent)
                        //    LIB.Diluters[i].SetConc(Comps[i].LowConc);
                        //这里必须设置了浓度才能计算步骤时间，所以这里也是必须的。在执行时用MakeConc间接调用了SetConc。溶剂用setVol计算时间
                        //if (Comps[i].IsSolvent)
                        //    LIB.Diluters[i].SetVol(solventvol);
                        //thisStepDuration = LIB.Diluters[i].TotalFwdDur * (99 + LIB.Diluters[i].Syringespd) / 99;
                        LIB.Diluters[i].Prepare(Comps[i].LowConc, Comps[i].IsSolvent, solventvol);//设置泵的注液参数
                        thisStepDuration = LIB.Diluters[i].GetDuration();//计算每个泵的注液时间
                        if (thisStepDuration > longeststepDuration)
                            longeststepDuration = thisStepDuration;
                        if (thisStepDuration > maxDurations[injectQueue.IndexOf(Comps[i].InjectOrder)])
                            maxDurations[injectQueue.IndexOf(Comps[i].InjectOrder)] = thisStepDuration;
                    }

                }

                //Duration = longeststepDuration / 1000; //转换为秒
                Duration = 0;
                foreach (double dur in maxDurations)
                    Duration += dur; // 1000;已经改为秒了
                DurUnit = "sec";
            }

            else if (OperType == Operation.EChem)
            {
                //CV和LSV：电压区间乘以段数除以扫速
                if (CHITechnique.Equals("CV"))
                {
                    float initialSegment;
                    if (ScanDir > 0.5) //正扫
                        initialSegment = EH - E0;
                    else
                        initialSegment = E0 - EL;
                    Duration = QuietTime + ((EH - EL) * (SegNum - 1) + initialSegment) / ScanRate;//只是估计时间，实际过程由CHI返回状态结束步骤
                }
                if (CHITechnique.Equals("LSV"))
                {
                    Duration = QuietTime + (EF - E0) / ScanRate;
                }
                if (CHITechnique.Equals("i-t"))
                    Duration = QuietTime + RunTime;
                DurUnit = "sec";
            }
            else if (OperType==Operation.Change)
            {
                int maxdist = 0;
                if (SimpleChange)
                {
                    //用最长的距离估算
                    maxdist = (int)((LIB.ThePositioner.MaxCol + 1)
                        * LIB.ThePositioner.cmperCol
                        * LIB.ThePositioner.PulsepercmX
                        + LIB.ThePositioner.cmperRow
                        * LIB.ThePositioner.PulsepercmY);
                    if (PickandPlace)
                        maxdist += (int)(2 * LIB.ThePositioner.PickHeight
                            * LIB.ThePositioner.cmperLay
                            * LIB.ThePositioner.PulsepercmZ);
                }
                else
                {
                    maxdist = (int)(IncX * LIB.ThePositioner.cmperCol
                        * LIB.ThePositioner.PulsepercmX
                        + IncY * LIB.ThePositioner.cmperRow
                        * LIB.ThePositioner.PulsepercmY
                        + IncZ * LIB.ThePositioner.cmperLay
                        * LIB.ThePositioner.PulsepercmZ);
                }
                Duration = (double) maxdist / LIB.ThePositioner.Speed;
                DurUnit = "sec";
            }
            else
            {
                if (DurUnit == "hr")
                    Duration = Duration * 3600;
                if (DurUnit == "min")
                    Duration = Duration * 60;
                if (DurUnit == "ms")
                    Duration = Duration / 1000;
                DurUnit = "sec";
                if (OperType == Operation.Flush)
                {
                    //重新调整冲洗时长为周期的整数倍
                    int cycleDuration; //进出周期长之和
                    int cycleNum;
                    cycleDuration = outletpump.CycleDuration + transferpump.CycleDuration + 2;
                    if (DurUnit == "cycle")
                        cycleNum = Convert.ToInt32(Duration);
                    else
                    {
                        cycleNum = Convert.ToInt32(Math.Ceiling((Duration - outletpump.CycleDuration) / cycleDuration));//必须减去最后一次排出，否则循环数每次运行都增加
                    }
                    if (cycleNum < 0)
                        cycleNum = 0;//不可以小于0

                    if (Duration > 0 && cycleNum < 1 && !EvacuateOnly)
                    {
                        cycleNum = 1;//除非把时间设置为0，否则，至少有一次循环
                        //SharedComponents.LogMsg += "[提示] 由于所指定冲洗时间过短，无法完成一次循环；现已自动将其设置为一次循环的时间。\r\n";
                        LogMsgBuffer.AddEntry(LIB.NamedStrings["Info"], LIB.NamedStrings["ChangeFlushCycle"]);
                    }
                    if (EvacuateOnly)
                        Duration = outletpump.CycleDuration;
                    else
                        Duration = cycleDuration * cycleNum + outletpump.CycleDuration;
                    FlushCycleNum = cycleNum;
                    //不能只在实验程序初始化时初始化硬件，因为这样只能保留最后一步的数据，必须在执行时初始化硬件参数
                    //比如第一次冲洗要10个循环，第二次5个循环，结果初始化完之后，两次都只有5个循环。
                    LIB.TheFlusher.Initialize();
                    //SharedComponents.TheFlusher.SetCycle(CycleNum);
                }
                if (OperType == Operation.Transfer)
                {
                    LIB.TheFlusher.Initialize();
                }
            }
        }
    }
}
