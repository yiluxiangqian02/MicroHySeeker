using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace eChemSDL
{
    public class ExpProgram
    {
        public List<ProgStep> Steps = new List<ProgStep>();
        public List<ProgStep> ParamEndValues = new List<ProgStep>(); //可变参数终值
        public List<ProgStep> ParamCurValues = new List<ProgStep>(); //可变参数当前值
        public List<ProgStep> ParamIntervals = new List<ProgStep>(); //可变参数步长
        //private List<int> ComboParamList = new List<int>();
        [JsonProperty]//用了这个私有域才会被序列化
        private List<List<double>> ParamMatrix = new List<List<double>>();
        [JsonProperty]
        private List<int> ParamIndex = new List<int>();//参数下标列表
        [JsonProperty]
        private List<int> ConstConcIndex = new List<int>();//恒定总浓度实验下标数组
        [JsonProperty]
        private List<int> UserSkipList = new List<int>(); //用户指定运行的程序编号，实际是用skip机制，默认没有skip
        public int ConstConcExpCount = 0;
        [JsonProperty]
        private List<bool> ComboExpToggle = new List<bool>();//总数和实验总数一样多，通过开关运行或跳过程序
        [JsonProperty]
        private int CurrentExpIndex;
        private int SelectExpIndex;//这个参数好像我定义了没什么用？怎么想的？
        [JsonProperty]
        private int TotalExpCount;
        private bool LoopParamChanged;
        //private bool ReachEnd;
        private int LoopParamIndex;
        //private bool SkipThis;//在恒定浓度实验时跳过不符合恒定浓度的实验
        //private string TestStr;
        private List<List<double>> ComboSelectParams = new List<List<double>>();//计算一次后保存一下有用的参数

        //ParamMatrix：参数值列表，每个参数的可能值，是一个List的List，每个参数可能取值对应一个List，例如：
        //A1: 0.3, 0.2, 0.1 三个可能取值List
        //A2: 0, 0.1, 0.2 三个可能取值List
        //A3: 0, 0.1 两个可能取值List
        //A4: 0 一个可能取值List
        //A5: 0 一个可能取值List
        //A6: 2 一个可能取值List
        //ParamIndex：参数下标列表，和ParamMatrix中的子List一一对应，指明每个子List里面取哪个值，例如：
        //ParamIndex = [0,2,1,0,0,0]对应ParamMatrix取出来的值列表是[0.3, 0.2, 0.1, 0, 0, 2]
        //ComboExpToggle：决定哪些参数值的组合（列表）会被执行，这个数组和实验总数一样多，例如上例的实验总数为3X3X2 = 18
        //ComboExpToggle = [T,T,T,T,T,T,T,.....](18项)当程序设置了总浓度要求时，某些参数组合会被设置为F，则不运行而跳过。


        public ExpProgram()
        {
            InitializeCombo();
        }

        public void AddStep(ProgStep ps)
        {
            Steps.Add(ps);
            ParamCurValues.Add(ps);
            ParamEndValues.Add(ps);
            ParamIntervals.Add(ps);
        }

        public void DeleteStep(int index)
        {
            Steps.RemoveAt(index);
            ParamCurValues.RemoveAt(index);
            ParamEndValues.RemoveAt(index);
            ParamIntervals.RemoveAt(index);
        }

        public void InsertStep(int index, ProgStep ps)
        {
            Steps.Insert(index, ps);
            ParamCurValues.Insert(index, ps);
            ParamEndValues.Insert(index, ps);
            ParamIntervals.Insert(index, ps);
        }

        public void UpdateStep(int index)
        {
            if (Steps.Count != ParamCurValues.Count)
                InitializeCombo();
            //{
                ParamCurValues.RemoveAt(index);
                ParamCurValues.Insert(index, LIB.Clone(Steps[index]));
                ParamEndValues.RemoveAt(index);
                ParamEndValues.Insert(index, LIB.Clone(Steps[index]));
                ParamIntervals.RemoveAt(index);
                ParamIntervals.Insert(index, LIB.Clone(Steps[index]));
            //}
        }

        public void InitializeCombo()//初始化组合实验，会覆盖掉当前参数值（重置进程）。
        {
            //ParamCurValues.Clear();
            //ParamIndex.Clear();
            //CurrentExpIndex = 0;
            //TotalExpCount = 1;
            //如果单步程序有更改，必须全部更改，不单单是步数更改了，步数不会不统一，因为统一了增加删除步骤
            //完全可以覆盖CurValues，只需要保存参数下标数组和当前实验指针就好了。
            ParamCurValues.Clear();
            foreach (ProgStep ps in Steps)
                ParamCurValues.Add(LIB.Clone(ps));

            if (ParamEndValues.Count != Steps.Count)
            {
                ParamEndValues.Clear();
                foreach (ProgStep ps in Steps)
                    ParamEndValues.Add(LIB.Clone(ps));
            }
            if (ParamIntervals.Count != Steps.Count)
            {
                ParamIntervals.Clear();
                foreach (ProgStep ps in Steps)
                    ParamIntervals.Add(LIB.Clone(ps));
            }

        }

        public bool ComboParamsValid()
        {
            return ParamMatrix.Count > 0;//初始化成功
        }

        public static List<double> CalParamValues(double startvalue, double endvalue, double interval)
        {
            List<double> values = new List<double>();
            double value;
            value = startvalue;
            double errorbar;
            errorbar = Math.Abs((startvalue - endvalue) * 10E-4);
            if (startvalue < endvalue)
            {
                if (interval == 0)
                    interval = Math.Abs((startvalue - endvalue) / LIB.DefaultCombCount);
                while (endvalue + Math.Abs(interval) - value > errorbar)//防止浮点数误差
                {
                    if (Math.Abs(value / (endvalue - startvalue)) < 10E-4)
                        value = 0;
                    values.Add(value);
                    value += Math.Abs(interval); 
                }
            }
            else if (startvalue > endvalue)
            {
                if (interval == 0)
                    interval = Math.Abs((startvalue - endvalue) / LIB.DefaultCombCount);
                while (value - endvalue + Math.Abs(interval) > errorbar)//防止浮点数误差
                {
                    if (Math.Abs(value / (endvalue - startvalue)) < 10E-4)
                        value = 0;
                    values.Add(value);
                    value -= Math.Abs(interval);//保险起见，防止有人输入负值
                }
            }
            else
                values.Add(value);
            return values;
        }

        //public List<string> ExpParam()//测试不确定层数循环时临时编写的函数，已通过其他实际函数实现
        //{
        //    List<string> expparam;
        //    expparam = new List<string>();
        //    List<int> paramindex;
        //    paramindex = new List<int>();//下标数组
        //    int maxindextotal = 0;
        //    for (int i = 0; i < ParamMatrix.Count; i++)
        //    {
        //        maxindextotal += ParamMatrix[i].Count-1;//最大下标之和，每个参数达到最大的下标时，加起来不能超过这个数，用于结束循环的判断
        //        paramindex.Add(0);//下标全初始化为0
        //    }

        //    bool complete = false;
        //    while (!complete)
        //    {

        //        int indextotal = 0;
        //        for (int i = 0; i < ParamMatrix.Count; i++)
        //            indextotal += paramindex[i];//把所有变量的下标加起来
        //        if (indextotal == maxindextotal)//不能超过下标最大值总和
        //            complete = true;

        //        string paramvalues = "";
        //        for (int i = 0; i < ParamMatrix.Count; i++)
        //            paramvalues += ParamMatrix[i][paramindex[i]].ToString() + ";"; 
        //        expparam.Add(paramvalues);

        //        //以下是计算下标组合的部分
        //        bool indexchanged = true;
        //        int nindex = ParamMatrix.Count - 1;  //从最后一个下标算起
        //        while (indexchanged && nindex >= 0)
        //        {
        //            //增加下标并检查是否达到上限，若达到就归零，并转向下一个参数
        //            if (++paramindex[nindex] > ParamMatrix[nindex].Count - 1)
        //            {
        //                paramindex[nindex] = 0;  
        //                indexchanged = true;
        //            }
        //            else
        //                indexchanged = false; // 没有达到上限，但是因为已经增加过值了，不能同时改变两个以上参数的值，所以设定退出循环。
        //            nindex--;  //转向下一个参数
        //        }

        //    }
        //    return expparam;
        //}

        public void FillParamMatrix()
        {
            ParamMatrix.Clear();
            if (Steps.Count != ParamEndValues.Count || Steps.Count != ParamIntervals.Count || Steps.Count != ParamCurValues.Count)
                return;
            for (int i = 0; i < Steps.Count; i++)
            {
                if (Steps[i].OperType == ProgStep.Operation.PrepSol)
                {
                    for (int j = 0; j < Steps[i].Comps.Count; j++)
                    {
                        if(!Steps[i].Comps[j].IsSolvent)
                            ParamMatrix.Add(CalParamValues(Steps[i].Comps[j].LowConc, ParamEndValues[i].Comps[j].LowConc, ParamIntervals[i].Comps[j].LowConc));
                    }
                }
                if (Steps[i].OperType == ProgStep.Operation.EChem)
                {
                    if (Steps[i].CHITechnique == "CV")
                    {
                        ParamMatrix.Add(CalParamValues(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
                        ParamMatrix.Add(CalParamValues(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
                        ParamMatrix.Add(CalParamValues(Steps[i].EH, ParamEndValues[i].EH, ParamIntervals[i].EH));
                        ParamMatrix.Add(CalParamValues(Steps[i].EL, ParamEndValues[i].EL, ParamIntervals[i].EL));
                        ParamMatrix.Add(CalParamValues(Steps[i].EF, ParamEndValues[i].EF, ParamIntervals[i].EF));
                        ParamMatrix.Add(CalParamValues(Steps[i].ScanRate, ParamEndValues[i].ScanRate, ParamIntervals[i].ScanRate));
                    }
                    if (Steps[i].CHITechnique == "LSV")
                    {
                        ParamMatrix.Add(CalParamValues(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
                        ParamMatrix.Add(CalParamValues(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
                        ParamMatrix.Add(CalParamValues(Steps[i].EF, ParamEndValues[i].EF, ParamIntervals[i].EF));
                        ParamMatrix.Add(CalParamValues(Steps[i].ScanRate, ParamEndValues[i].ScanRate, ParamIntervals[i].ScanRate));
                    }
                    if (Steps[i].CHITechnique == "i-t")
                    {
                        ParamMatrix.Add(CalParamValues(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
                        ParamMatrix.Add(CalParamValues(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
                        ParamMatrix.Add(CalParamValues(Steps[i].RunTime, ParamEndValues[i].RunTime, ParamIntervals[i].RunTime));
                    }
                }
                if (Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush || Steps[i].OperType == ProgStep.Operation.Transfer)
                {
                    ParamMatrix.Add(CalParamValues(Steps[i].Duration, ParamEndValues[i].Duration, ParamIntervals[i].Duration));
                }
            }
            TotalExpCount = 1;
            CurrentExpIndex = 0;//TODO:要复位指针吗？
            ParamIndex.Clear();
            for (int i = 0; i < ParamMatrix.Count; i++)
            {
                ParamIndex.Add(0);//下标全初始化为0
                TotalExpCount *= ParamMatrix[i].Count;
            }
            ComboExpToggle.Clear();
            for(int i = 0; i < TotalExpCount; i++)
                ComboExpToggle.Add(true);
            LoadParamValues();
        }

        //public int ComboExpCount()
        //{
        //    int count = 1;
        //    ComboParamList.Clear();
        //    if (Steps.Count != ParamEndValues.Count || Steps.Count != ParamIntervals.Count || Steps.Count != ParamCurValues.Count)
        //        return -1;
        //    for (int i = 0; i < Steps.Count; i++)
        //    {
        //        if (Steps[i].OperType == ProgStep.Operation.PrepSol)
        //        {
        //            for (int j = 0; j < Steps[i].Comps.Count; j++)
        //            {
        //                ComboParamList.Add(ParamDividedCount(Steps[i].Comps[j].LowConc, ParamEndValues[i].Comps[j].LowConc, ParamIntervals[i].Comps[j].LowConc));
        //            }
        //        }
        //        if (Steps[i].OperType == ProgStep.Operation.EChem)
        //        {
        //            if (Steps[i].CHITechnique == "CV")
        //            {
        //                ComboParamList.Add(ParamDividedCount(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].EH, ParamEndValues[i].EH, ParamIntervals[i].EH));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].EL, ParamEndValues[i].EL, ParamIntervals[i].EL));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].EF, ParamEndValues[i].EF, ParamIntervals[i].EF));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].ScanRate, ParamEndValues[i].ScanRate, ParamIntervals[i].ScanRate));
        //            }
        //            if (Steps[i].CHITechnique == "LSV")
        //            {
        //                ComboParamList.Add(ParamDividedCount(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].EF, ParamEndValues[i].EF, ParamIntervals[i].EF));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].ScanRate, ParamEndValues[i].ScanRate, ParamIntervals[i].ScanRate));
        //            }
        //            if (Steps[i].CHITechnique == "i-t")
        //            {
        //                ComboParamList.Add(ParamDividedCount(Steps[i].E0, ParamEndValues[i].E0, ParamIntervals[i].E0));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].QuietTime, ParamEndValues[i].QuietTime, ParamIntervals[i].QuietTime));
        //                ComboParamList.Add(ParamDividedCount(Steps[i].RunTime, ParamEndValues[i].RunTime, ParamIntervals[i].RunTime));
        //            }
        //        }
        //        if (Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush)
        //        {
        //            ComboParamList.Add(ParamDividedCount(Steps[i].Duration, ParamEndValues[i].Duration, ParamIntervals[i].Duration));
        //        }
        //    }
        //    for (int i = 0; i < ComboParamList.Count; i++)
        //    {
        //        count *= ComboParamList[i];
        //    }
        //    return count;
        //}

        public bool ComboCompleted()
        {
            if (CurrentExpIndex == TotalExpCount - 1)
                return true;
            else
                return false;
        }

        //public string GetComboParamSet()
        //{
        //    //NextCombParamSet();
        //    return TestStr;
        //}

        public int ComboProgress()
        {
            return CurrentExpIndex + 1;
        }

        public int ComboExpCount()
        {
            return TotalExpCount;
        }

        public void NextComboParams()
        {
            if (CurrentExpIndex < TotalExpCount - 1)
                CurrentExpIndex++;
            //CurrentExpIndex++;
            //if (CurrentExpIndex >= TotalExpCount)
            //    CurrentExpIndex = TotalExpCount - 1;
            ComboSeekNLoad(CurrentExpIndex);
        }

        public void NextSelectComboParams()
        {
            if(SelectComboProgress() < ConstConcExpCount)
            {
                ComboSeekNLoad(ConstConcIndex[SelectComboProgress()]);
                //NextComboParamIndexes();
                //while (ComboExpToggle[CurrentExpIndex] != true)
                //    NextComboParamIndexes();
                //LoadParamValues();
            }
        }

        public void PreviousSelectComboParams()
        {
            if (SelectComboProgress() > 1)
            {
                ComboSeekNLoad(ConstConcIndex[SelectComboProgress() - 2]);
            }
        }

        public void SelectComboSeekNLoad(int selectindex)
        {
            if (selectindex >= 1 && selectindex <= ConstConcExpCount)
            {
                ComboSeekNLoad(ConstConcIndex[selectindex - 1]);
            }
        }

        public void ResetComboParams()
        {
            CurrentExpIndex = 0;
            RefreshParams();
            ComboSeekNLoad(0);
        }

        public void PreviousComboParams()
        {
            CurrentExpIndex--;
            if (CurrentExpIndex <= 0)
                CurrentExpIndex = 0;
            ComboSeekNLoad(CurrentExpIndex);
        }

        public void ComboSeekNLoad(int expindex)//为了保险用笨方法，每次从头搜，每次都载入参数
        {
            CurrentExpIndex = 0;
            ParamIndex.Clear();
            for (int i = 0; i < ParamMatrix.Count; i++)
                ParamIndex.Add(0);//下标全初始化为0
            if (expindex >= 0 && expindex < TotalExpCount)
            {
                while (CurrentExpIndex < expindex)
                {
                    NextComboParamIndexes();
                }
                LoadParamValues();
            }
        }

        public bool SelectCombParams()//判定当前程序是否选中应该执行
        {
            if(!ComboExpToggle[CurrentExpIndex] || UserSkipList.Contains(SelectComboProgress()))
            {
                while ((!ComboExpToggle[CurrentExpIndex] || UserSkipList.Contains(SelectComboProgress())) && CurrentExpIndex < TotalExpCount - 1)
                    NextComboParamIndexes();
            }
            LoadParamValues();
            return ComboExpToggle[CurrentExpIndex];
            //if (increment == 0)//如果没有移动，就移动一个
            //{
            //    NextCombParamSet();
            //    while (!ComboExpToggle[CurrentExpIndex] && CurrentExpIndex < TotalExpCount -1)
            //        NextCombParamSet();
            //    LoadParamValues();
            //}
        }

        public void NextComboParamIndexes()//只改变当前参数下标，不载入参数，需要用LoadParamValues载入
        {
            //if (CurrentExpIndex == 0)
            //    FillParamMatrix();//在第一次实验时初始化各参数，应该只有在发生了更改时才重新设置
            //if (CurrentExpIndex == TotalExpCount)
            //    return;
            //else
            //    LoadParamValues();

            //TestStr = CurrentExpIndex.ToString() + ":\r\n[";
            //for (int i = 0; i < ParamMatrix.Count; i++)
            //{
            //    TestStr += ParamMatrix[i][ParamIndex[i]].ToString() + "; ";//TODO:测试语句，以后删掉
            //}
            //TestStr += "]\r\n";

            //LoadParamValues();

            LoopParamChanged = true;
            LoopParamIndex = ParamMatrix.Count - 1;
            while (LoopParamChanged && LoopParamIndex >= 0)
            {
                //增加下标并检查是否达到上限，若达到就归零，并转向下一个参数
                if (++ParamIndex[LoopParamIndex] > ParamMatrix[LoopParamIndex].Count - 1)
                {
                    ParamIndex[LoopParamIndex] = 0;
                    LoopParamChanged = true;
                }
                else
                    LoopParamChanged = false; // 没有达到上限，但是因为已经增加过值了，不能同时改变两个以上参数的值，所以设定退出循环。
                LoopParamIndex--;  //转向下一个参数
            }
            if(CurrentExpIndex < TotalExpCount -1)
                CurrentExpIndex++;
        }

        public void RefreshParams() //主要是看一下有没有恒定浓度的步骤
        {
            List<double> paramset = new List<double>();
            CurrentExpIndex = 0;
            FillParamMatrix();
            ComboSelectParams.Clear();
            for (int i = 0; i < TotalExpCount; i++)
            {
                bool constconc = false;
                if (ComboExpToggle[CurrentExpIndex])
                    constconc = true;
                if(constconc)
                {
                    paramset.Clear();
                    for (int j = 0; j < ParamIndex.Count; j++)
                        paramset.Add(ParamMatrix[j][ParamIndex[j]]);
                    ComboSelectParams.Add(new List<double>(paramset));
                }
                NextComboParamIndexes();
                LoadParamValues();

                //SharedComponents.LogMsg += TestStr;
            }
            CurrentExpIndex = 0;
            ParamIndex.Clear();
            for (int i = 0; i < ParamMatrix.Count; i++)
                ParamIndex.Add(0);//下标全初始化为0
        }

        public int SelectComboProgress()
        {
            int progress;
            progress = ConstConcIndex.IndexOf(CurrentExpIndex);
            if (progress < 0)
                progress = SelectExpIndex;
            else
                SelectExpIndex = progress;
            return progress + 1;
        }

        public string ListSelectParams()
        {
            string listselectparams = "";
            if (ComboSelectParams.Count == 0)
            {
                return LIB.NamedStrings["BeforeListParam"];// "请先复位程序或在编辑器里保存修改，再列出参数。\r\n";
            }
            for (int i = 0; i < ConstConcIndex.Count; i++)//这两个数组Count不一样
            {
                listselectparams += (ConstConcIndex[i] + 1).ToString() + ":[";
                for (int j = 0; j < ComboSelectParams[i].Count; j++)
                    listselectparams += ((float)ComboSelectParams[i][j]).ToString() + ",";
                listselectparams = listselectparams.TrimEnd(',');
                listselectparams += "]\r\n";
            }
            return listselectparams;
        }

        public List<int> SetConstConcExp()
        {
            ConstConcIndex.Clear();
            RefreshParams();
            for (int i = 0; i < ComboExpToggle.Count; i++)
            {
                if (ComboExpToggle[i])
                    ConstConcIndex.Add(i);
            }
            ConstConcExpCount = ConstConcIndex.Count;
            return ConstConcIndex;
        }

        public void LoadParamValues()
        {
            if (Steps.Count != ParamEndValues.Count || Steps.Count != ParamIntervals.Count || Steps.Count != ParamCurValues.Count)
                return;
            int paramindex = 0;//实验中的第几个可变参数
            for (int i = 0; i < Steps.Count; i++)
            {
                if (Steps[i].OperType == ProgStep.Operation.PrepSol)
                {
                    double totalconc = 0;
                    for (int j = 0; j < Steps[i].Comps.Count; j++)
                    {
                        if(!Steps[i].Comps[j].IsSolvent)
                        {
                            ParamCurValues[i].Comps[j].LowConc = ParamMatrix[paramindex][ParamIndex[paramindex]];//第paramindex参数的第ParamIndex[paramindex]个值
                            if (Steps[i].Comps[j].InConstConc)
                                totalconc += ParamCurValues[i].Comps[j].LowConc;
                            paramindex++;
                        }
                    }
                    if (Steps[i].ConstTotalConc && Math.Abs(totalconc - Steps[i].TotalConc) > totalconc * 10E-6)//只有在恒总浓度且浓度不等于总浓度时取消实验，误差设置为总浓度的10E-6，因为发现10E-3好像不够小
                        ComboExpToggle[CurrentExpIndex] = false;
                    //else
                    //{
                    //    //ComboExpToggle[CurrentExpIndex] = true;//TODO:后续的steps会把这个实验设为TRUE!所以最后所有实验都是true
                    //    //if (!ConstConcIndex.Contains(CurrentExpIndex))
                    //    //    ConstConcIndex.Add(CurrentExpIndex);
                    //}


                }
                if (Steps[i].OperType == ProgStep.Operation.EChem)
                {
                    if (Steps[i].CHITechnique == "CV")
                    {
                        ParamCurValues[i].QuietTime = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].E0 = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].EH = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].EL = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].EF = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].ScanRate = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                    }
                    if (Steps[i].CHITechnique == "LSV")
                    {
                        ParamCurValues[i].QuietTime = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].E0 = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].EF = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].ScanRate = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;

                    }
                    if (Steps[i].CHITechnique == "i-t")
                    {
                        ParamCurValues[i].QuietTime = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].E0 = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                        ParamCurValues[i].RunTime = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                        paramindex++;
                    }
                }
                if (Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush || Steps[i].OperType == ProgStep.Operation.Transfer)
                {
                    ParamCurValues[i].Duration = (float)ParamMatrix[paramindex][ParamIndex[paramindex]];
                    paramindex++;
                }
            }
        }

        public bool UserSkip(int SelectComboIndex)
        {
            return UserSkipList.Contains(SelectComboIndex);
        }

        public void UpdateUserSkipList(List<int> list)
        {
            UserSkipList = LIB.Clone(list);
        }
    }
}
