using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class ComboExpEditor : Form
    {
        private BindingList<ProgStep> Steps;
        private List<ProgStep> ParameterEndvalues;
        private List<ProgStep> ParameterIntervals;
        private TableLayoutPanel ParameterPanel = new TableLayoutPanel();

        public ComboExpEditor()
        {
            InitializeComponent();
        }

        private void ComboExpEditor_Load(object sender, EventArgs e)
        {
            GroupBoxParam.SuspendLayout();
            ParameterPanel.SuspendLayout();
            if (LIB.LastExp.Steps.Count <= 0)
            {
                ProgStep ps = new ProgStep();
                LIB.LastExp.Steps.Add(ps);
            }

            //SharedComponents.LastExp.InitializeCombo();//不应该放在Load这里，会破坏进行中的实验
            Steps = new BindingList<ProgStep>(LIB.LastExp.Steps);
            ParameterEndvalues = LIB.LastExp.ParamEndValues;//不需要重新创建一个对象，只用引用就可以
            ParameterIntervals = LIB.LastExp.ParamIntervals;

            StepList.DataSource = Steps;
            
            ParameterPanel.AutoScroll = false;
            ParameterPanel.HorizontalScroll.Enabled = false;
            ParameterPanel.HorizontalScroll.Visible = false;
            ParameterPanel.HorizontalScroll.Maximum = 0;
            ParameterPanel.AutoScroll = true;

            Label desclabelhead = new Label();
            desclabelhead.Text = LIB.NamedStrings["Param"];// "变量";
            desclabelhead.Anchor = AnchorStyles.Left;
            desclabelhead.AutoSize = true;
            Label startvaluelabelhead = new Label();
            startvaluelabelhead.Text = LIB.NamedStrings["InitialValue"];//"初值";
            startvaluelabelhead.AutoSize = true;
            Label endvaluelabelhead = new Label();
            endvaluelabelhead.Text = LIB.NamedStrings["FinalValue"];//"终值";
            endvaluelabelhead.AutoSize = true;
            Label intervallabelhead = new Label();
            intervallabelhead.Text = LIB.NamedStrings["Interval"];//"间隔";
            intervallabelhead.AutoSize = true;
            ParameterPanel.Controls.Add(desclabelhead, 2, 0);
            ParameterPanel.Controls.Add(startvaluelabelhead, 3, 0);
            ParameterPanel.Controls.Add(endvaluelabelhead, 4, 0);
            ParameterPanel.Controls.Add(intervallabelhead, 5, 0);

            int row = 1;
            for (int i = 0; i < Steps.Count; i++)
            {
                Label indexlabel = new Label();
                indexlabel.Text = (i + 1).ToString("D3") + ":" + Steps[i].GetDesc().Substring(0, Steps[i].GetDesc().IndexOf(']') + 1);
                indexlabel.AutoSize = true;
                ParameterPanel.Controls.Add(indexlabel, 0, row);
                row++;
                //Label desclabel = new Label();
                //desclabel.Text = Steps[i].GetDesc().Substring(1, Steps[i].GetDesc().IndexOf(']')-1);
                //desclabel.AutoSize = true;
                //ParameterPanel.Controls.Add(desclabel, 0, row);

                if (Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush)
                {
//                    AddControlForParameter(Steps[i].Duration, "持续(秒)", ParameterEndvalues[i].Duration, ParameterIntervals[i].Duration, i, row);
                    AddControlForParameter(Steps[i].Duration, LIB.NamedStrings["DurationSec"], ParameterEndvalues[i].Duration, ParameterIntervals[i].Duration, i, row);
                    row++;
                }
                if (Steps[i].OperType == ProgStep.Operation.EChem)
                {
                    if (Steps[i].CHITechnique == "CV")
                    {
                        //AddControlForParameter(Steps[i].QuietTime, "静置(秒)", ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        AddControlForParameter(Steps[i].QuietTime, LIB.NamedStrings["QuietTime"], ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].E0, "起始电位(V)", ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        AddControlForParameter(Steps[i].E0, LIB.NamedStrings["E0"], ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].EH, "最高电位(V)", ParameterEndvalues[i].EH, ParameterIntervals[i].EH, i, row);
                        AddControlForParameter(Steps[i].EH, LIB.NamedStrings["EH"], ParameterEndvalues[i].EH, ParameterIntervals[i].EH, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].EL, "最低电位(V)", ParameterEndvalues[i].EL, ParameterIntervals[i].EL, i, row);
                        AddControlForParameter(Steps[i].EL, LIB.NamedStrings["EL"], ParameterEndvalues[i].EL, ParameterIntervals[i].EL, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].EF, "终止电位(V)", ParameterEndvalues[i].EF, ParameterIntervals[i].EF, i, row);
                        AddControlForParameter(Steps[i].EF, LIB.NamedStrings["EF"], ParameterEndvalues[i].EF, ParameterIntervals[i].EF, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].ScanRate, "扫速(V/s)", ParameterEndvalues[i].ScanRate, ParameterIntervals[i].ScanRate, i, row);
                        AddControlForParameter(Steps[i].ScanRate, LIB.NamedStrings["ScanRate"], ParameterEndvalues[i].ScanRate, ParameterIntervals[i].ScanRate, i, row);
                        row++;
                    }
                    if (Steps[i].CHITechnique == "LSV")
                    {
                        //AddControlForParameter(Steps[i].QuietTime, "静置(秒)", ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        AddControlForParameter(Steps[i].QuietTime, LIB.NamedStrings["QuietTime"], ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].E0, "起始电位(V)", ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        AddControlForParameter(Steps[i].E0, LIB.NamedStrings["E0"], ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].EF, "终止电位(V)", ParameterEndvalues[i].EF, ParameterIntervals[i].EF, i, row);
                        AddControlForParameter(Steps[i].EF, LIB.NamedStrings["EF"], ParameterEndvalues[i].EF, ParameterIntervals[i].EF, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].ScanRate, "扫速(V/s)", ParameterEndvalues[i].ScanRate, ParameterIntervals[i].ScanRate, i, row);
                        AddControlForParameter(Steps[i].ScanRate, LIB.NamedStrings["ScanRate"], ParameterEndvalues[i].ScanRate, ParameterIntervals[i].ScanRate, i, row);
                        row++;
                    }
                    if (Steps[i].CHITechnique == "i-t")
                    {
                        //AddControlForParameter(Steps[i].QuietTime, "静置(秒)", ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        AddControlForParameter(Steps[i].QuietTime, LIB.NamedStrings["QuietTime"], ParameterEndvalues[i].QuietTime, ParameterIntervals[i].QuietTime, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].E0, "起始电位(V)", ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        AddControlForParameter(Steps[i].E0, LIB.NamedStrings["E0"], ParameterEndvalues[i].E0, ParameterIntervals[i].E0, i, row);
                        row++;
                        //AddControlForParameter(Steps[i].RunTime, "运行(秒)", ParameterEndvalues[i].RunTime, ParameterIntervals[i].RunTime, i, row);
                        AddControlForParameter(Steps[i].RunTime, LIB.NamedStrings["RunTime"], ParameterEndvalues[i].RunTime, ParameterIntervals[i].RunTime, i, row);
                        row++;
                    }
                }

                if (Steps[i].OperType == ProgStep.Operation.PrepSol)
                {
                    List<List<double>> conclist = new List<List<double>>();
                    for (int j = 0; j < Steps[i].Comps.Count; j++)
                    {
                        if(!Steps[i].Comps[j].IsSolvent)
                            AddControlForParameter(Steps[i].Comps[j].LowConc, "[" + Steps[i].Comps[j].Solute + "]", ParameterEndvalues[i].Comps[j].LowConc, ParameterIntervals[i].Comps[j].LowConc, i, row);
                        if (Steps[i].Comps[j].InConstConc)
                            conclist.Add(ExpProgram.CalParamValues(Steps[i].Comps[j].LowConc, ParameterEndvalues[i].Comps[j].LowConc, ParameterIntervals[i].Comps[j].LowConc));
                        row++;
                    }
                    CheckBox ConstTotalConc = new CheckBox();
                    ConstTotalConc.Text = LIB.NamedStrings["IncludeInTotalConc"];//"以上勾选计入总浓度";
                    ConstTotalConc.AutoSize = true;
                    ConstTotalConc.Name = i.ToString() + "ConstTotalConc";
                    ConstTotalConc.Anchor = AnchorStyles.Left;
                    ConstTotalConc.Checked = Steps[i].ConstTotalConc;
                    ConstTotalConc.CheckedChanged += ToggleTotalConc; 
                    ComboBox totalConc = new ComboBox();
                    //List<string> totalconclist = new List<string>();//这些在GetExpCount()中完成，不需重复
                    //totalconclist = TotalConcList(conclist);
                    //totalconclist.Sort();
                    //totalConc.Items.AddRange(totalconclist.ToArray());
                    //if (totalconclist.Contains(Steps[i].TotalConc.ToString()))
                    //    totalConc.Text = Steps[i].TotalConc.ToString();
                    //else
                    //    totalConc.SelectedIndex = 0;
                    totalConc.Name = i.ToString() + "totalConc";
                    totalConc.Width = 60;
                    totalConc.DropDownStyle = ComboBoxStyle.DropDownList;
                    totalConc.Enabled = Steps[i].ConstTotalConc;
                    ParameterPanel.Controls.Add(ConstTotalConc, 1, row);
                    ParameterPanel.SetColumnSpan(ConstTotalConc, 3);
                    ParameterPanel.Controls.Add(totalConc, 4, row);
                    row++;
                }
            }
            ParameterPanel.Controls.Add(new Label(),0,row);//调节控件位置，否则最后一个标签会掉到下面
            ParameterPanel.Dock = DockStyle.Fill;
            ParameterPanel.ResumeLayout(true);
            GroupBoxParam.Controls.Add(ParameterPanel);
            StepList.SelectedIndex = -1;
            GroupBoxParam.ResumeLayout(true);
            foreach(Control ctl in ParameterPanel.Controls)
            {
                if (ctl is TextBox || ctl is CheckBox)
                    ctl.Validated += GetExpCount;
            }
            GetExpCount(this, new EventArgs());
            MinimumSize = new Size(Width, Height);
        }

        public List<string> TotalConcList(List<List<double>> conclist)
        {
            List<string> totalconclist = new List<string>();
            List<int> paramindex = new List<int>();
            int maxindextotal = 0;
            bool complete = false;
            bool indexchanged = true;

            for (int i = 0; i < conclist.Count; i++)
            {
                maxindextotal += (conclist[i].Count - 1);//最大下标之和，每个参数达到最大的下标时，加起来不能超过这个数，用于结束循环的判断
                paramindex.Add(0);//下标全初始化为0
            }

            while (!complete)
            {
                int indextotal = 0;
                double totalconc = 0;
                for (int i = 0; i < conclist.Count; i++)
                {
                    indextotal += paramindex[i];//把所有变量的下标加起来
                    totalconc += conclist[i][paramindex[i]];
                }
                if (Math.Abs(totalconc) < 10E-12)
                    totalconc = 0;//防止出现一个无限于接近于0的双精度数1.387E-17之类的。我这个10E-12是随意定的。
                if (indextotal == maxindextotal)//不能超过下标最大值总和
                    complete = true;
                if(!totalconclist.Contains(totalconc.ToString()))
                    totalconclist.Add(totalconc.ToString());
                //以下是计算下标组合的部分
                indexchanged = true;
                int nindex = conclist.Count - 1;  //从最后一个下标算起
                while (indexchanged && nindex >= 0)
                {
                    //增加下标并检查是否达到上限，若达到就归零，并转向下一个参数
                    if (++paramindex[nindex] > conclist[nindex].Count - 1)
                    {
                        paramindex[nindex] = 0;
                        indexchanged = true;
                    }
                    else
                        indexchanged = false; // 没有达到上限，但是因为已经增加过值了，不能同时改变两个以上参数的值，所以设定退出循环。
                    nindex--;  //转向下一个参数
                }
            }
            totalconclist.Sort();
            return totalconclist;
        }

        private void ToggleTotalConc(object sender, EventArgs e)
        {
            CheckBox constTotalConc;
            constTotalConc = (CheckBox)sender;
            int i = constTotalConc.Name.IndexOf("ConstTotalConc");
            string stepindex = constTotalConc.Name.Substring(0, i);
            if (((CheckBox)sender).Checked)
            {
                ParameterPanel.Controls[stepindex + "totalConc"].Enabled = true;
                foreach (Control ctl in ParameterPanel.Controls)
                {
                    if (ctl is CheckBox && ctl.Name.IndexOf(stepindex) == 0 && ctl.Name.Contains("Check"))
                        ((CheckBox)ctl).Enabled = true;
                }
            }
            else
            {
                ParameterPanel.Controls[stepindex + "totalConc"].Enabled = false;
                foreach (Control ctl in ParameterPanel.Controls)
                {
                    if (ctl is CheckBox && ctl.Name.IndexOf(stepindex) == 0 && ctl.Name.Contains("Check"))
                        ((CheckBox)ctl).Enabled = false;
                }
            }
        }

        private void GetExpCount(object sender, System.EventArgs e)
        {
            double endvalue;
            double interval;
            double startvalue;
            string txtstart;
            string txtend;
            string txtint;
            List<int> indexpcount = new List<int>();
            int expcounts;
            expcounts = 1;
            if (Steps.Count != ParameterEndvalues.Count || Steps.Count != ParameterIntervals.Count)
                MessageBox.Show(LIB.NamedStrings["ParamCountError"]);// "参数的个数不匹配！");
            //SaveChanges();
            foreach (Control ctl in ParameterPanel.Controls)
            {
                int index = ctl.Name.IndexOf("EndValue");
                if (index > 0)
                {
                    string indexdesc = ctl.Name.Substring(0, index);
                    txtstart = ParameterPanel.Controls[indexdesc + "StartValue"].Text;
                    txtend = ctl.Text;
                    if (!txtstart.Equals(txtend))
                    {
                        startvalue = Convert.ToDouble(string.IsNullOrEmpty(txtstart) ? "0" : txtstart);
                        endvalue = Convert.ToDouble(string.IsNullOrEmpty(txtend) ? "0" : txtend);
                        txtint = ParameterPanel.Controls[indexdesc + "Interval"].Text;
                        interval = Convert.ToDouble(string.IsNullOrEmpty(txtint) ? "0" : txtint);
                        if (Math.Abs(interval) < Math.Abs((endvalue - startvalue) * 0.001) || Math.Abs(interval) / Math.Abs(endvalue - startvalue) > 1.001)
                        {
                            interval = Math.Round((endvalue - startvalue) / LIB.DefaultCombCount, 3);//自动10个实验？还是定义一个常量？
                            ParameterPanel.Controls[indexdesc + "Interval"].Text = interval.ToString();
                            ParameterPanel.Controls[indexdesc + "Label"].BackColor = Color.PowderBlue;
                            expcounts *= LIB.DefaultCombCount;
                            indexpcount.Add(LIB.DefaultCombCount);
                        }
                        else
                        {
                            int count = Convert.ToInt32(Math.Abs((endvalue - startvalue) / interval)) + 1;
                            ParameterPanel.Controls[indexdesc + "Label"].BackColor = Color.PowderBlue;
                            expcounts *= count;
                            indexpcount.Add(count);
                        }

                    }
                    else
                        ParameterPanel.Controls[indexdesc + "Label"].BackColor = BackColor;
                }
                //更新总浓度列表值
                if (ctl is ComboBox && ctl.Enabled)
                {
                    index = ctl.Name.IndexOf("totalConc");
                    int stepindex = Convert.ToInt32(ctl.Name.Substring(0,index));
                    List<List<double>> conclist = new List<List<double>>();
                    for (int j = 0; j < Steps[stepindex].Comps.Count; j++)
                    {
                        if (Steps[stepindex].Comps[j].InConstConc && !Steps[stepindex].Comps[j].IsSolvent)
                            conclist.Add(ExpProgram.CalParamValues(Steps[stepindex].Comps[j].LowConc, ParameterEndvalues[stepindex].Comps[j].LowConc, ParameterIntervals[stepindex].Comps[j].LowConc));
                    }
                    if(conclist.Count > 0)
                    {
                        List<string> totalconclist = new List<string>();
                        totalconclist = TotalConcList(conclist);
                        totalconclist.Sort();
                        ((ComboBox)ctl).Items.Clear();
                        ((ComboBox)ctl).Items.AddRange(TotalConcList(conclist).ToArray());
                        if (totalconclist.Contains(Steps[stepindex].TotalConc.ToString()))
                            ((ComboBox)ctl).Text = Steps[stepindex].TotalConc.ToString();
                        else
                            ((ComboBox)ctl).SelectedIndex = 0;
    
                    }
                }
            }

            //曾经是这么写的
            #region
            //for (int i = 0; i < Steps.Count; i++)
            //{
            //    if (Steps[i].OperType == ProgStep.Operation.PrepSol)
            //    {
            //        for (int j = 0; j < Steps[i].Comps.Count; j++)
            //        {
            //            txtend = ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "EndValue"].Text;
            //            endvalue = Convert.ToDouble(string.IsNullOrEmpty(txtend) ? "0" : txtend);
            //            if (Steps[i].Comps[j].LowConc != endvalue)
            //            {
            //                txtint = ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "Interval"].Text;
            //                interval = Convert.ToDouble(string.IsNullOrEmpty(txtint) ? "0" : txtint);
            //                if (Math.Abs(interval) < Math.Abs((endvalue - Steps[i].Comps[j].LowConc) * 10E-3) || Math.Abs(interval) > Math.Abs(endvalue - Steps[i].Comps[j].LowConc))
            //                {
            //                    interval = Math.Round((endvalue - Steps[i].Comps[j].LowConc) / SharedComponents.DefaultCombCount, 3);//自动10个实验？还是定义一个常量？
            //                    ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "Interval"].Text = interval.ToString();
            //                    ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "Label"].BackColor = Color.PowderBlue;
            //                    expcounts *= (SharedComponents.DefaultCombCount + 1);
            //                }
            //                else
            //                {
            //                    int count = Convert.ToInt32(Math.Abs((endvalue - Steps[i].Comps[j].LowConc) / interval)) + 1;
            //                    ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "Label"].BackColor = Color.PowderBlue;
            //                    expcounts *= count;
            //                }
            //            }
            //            else
            //                ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solvate + "]" + "Label"].BackColor = BackColor;
            //        }
            //    }
            //    if (Steps[i].OperType == ProgStep.Operation.EChem || Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush)
            //    {
            //        foreach(Control ctl in ParameterPanel.Controls)
            //        {
            //            int index = ctl.Name.IndexOf("EndValue");
            //            if (ctl.Name.StartsWith(i.ToString()) && index > 0)
            //            {
            //                string indexdesc = ctl.Name.Substring(0, index);
            //                txtstart = ParameterPanel.Controls[indexdesc + "StartValue"].Text;
            //                txtend = ctl.Text;
            //                if (!txtstart.Equals(txtend))
            //                {
            //                    startvalue = Convert.ToDouble(string.IsNullOrEmpty(txtstart) ? "0" : txtstart);
            //                    endvalue = Convert.ToDouble(string.IsNullOrEmpty(txtend) ? "0" : txtend);
            //                    txtint = ParameterPanel.Controls[indexdesc + "Interval"].Text;
            //                    interval = Convert.ToDouble(string.IsNullOrEmpty(txtint) ? "0" : txtint);
            //                    if (Math.Abs(interval) < Math.Abs((endvalue - startvalue) * 10E-3) || Math.Abs(interval) > Math.Abs(endvalue - startvalue))
            //                    {
            //                        interval = Math.Round((endvalue - startvalue) / SharedComponents.DefaultCombCount, 3);//自动10个实验？还是定义一个常量？
            //                        ParameterPanel.Controls[indexdesc + "Interval"].Text = interval.ToString();
            //                        ParameterPanel.Controls[indexdesc + "Label"].BackColor = Color.PowderBlue;
            //                        expcounts *= SharedComponents.DefaultCombCount;
            //                    }
            //                    else
            //                    {
            //                        int count = Convert.ToInt32(Math.Abs((endvalue - startvalue) / interval)) + 1;
            //                        ParameterPanel.Controls[indexdesc + "Label"].BackColor = Color.PowderBlue;
            //                        expcounts *= count;
            //                    }
            //                }
            //                else
            //                    ParameterPanel.Controls[indexdesc + "Label"].BackColor = BackColor;
            //            }
            //        }
            //    }
            //}
            #endregion
            expcounts = Math.Abs(expcounts);
            MsgBox.Text = LIB.NamedStrings["CmbExpCnt"] + "：\r\n";// "组合实验数目：\r\n";
            foreach (int i in indexpcount)
                MsgBox.Text += i.ToString() + "X\r\n";
            MsgBox.Text += "-----\r\n" + expcounts.ToString() + "\r\n";
            MsgBox.Text += LIB.NamedStrings["SaveToCalCnt"] + "\r\n"; //"如果指定总浓度，保存修改以计算实际实验数目。\r\n";
        }

        private void AddControlForParameter(double value, string desc, double endvalue, double interval, int stepindex, int row)
        {
            Label startvaluelabel = new Label();
            TextBox txtParam = new TextBox();
            TextBox txtInterval = new TextBox();

            if (Steps[stepindex].OperType == ProgStep.Operation.PrepSol)
            {
                CheckBox inconstconc = new CheckBox();
                Label solvatelabel = new Label();
                inconstconc.Name = stepindex.ToString() + desc + "Check";
                solvatelabel.Text = desc;
                solvatelabel.Name = stepindex.ToString() + desc + "Label";
                //inconstconc.Text = desc;
                inconstconc.AutoSize = true;
                SingleSolution ss;
                ss = Steps[stepindex].Comps.FirstOrDefault(name => "[" + name.Solute + "]" == desc);
                if (ss != null)
                {
                    inconstconc.Checked = ss.InConstConc;
                    inconstconc.Enabled = Steps[stepindex].ConstTotalConc;
                    ParameterPanel.Controls.Add(inconstconc, 1, row);
                    ParameterPanel.Controls.Add(solvatelabel, 2, row);
                }
            }
            else
            {
                Label paramlabel = new Label();
                paramlabel.Name = stepindex.ToString() + desc + "Label";
                paramlabel.Text = desc;
                paramlabel.TextAlign = ContentAlignment.MiddleRight;
                paramlabel.Anchor = AnchorStyles.Right | AnchorStyles.Top | AnchorStyles.Bottom;
                paramlabel.AutoSize = true;
                ParameterPanel.Controls.Add(paramlabel, 2, row);
            }

            startvaluelabel.Name = stepindex.ToString() + desc + "StartValue";
            startvaluelabel.Text = ((float)value).ToString();
            startvaluelabel.TextAlign = ContentAlignment.MiddleRight;
            startvaluelabel.Anchor = AnchorStyles.Right | AnchorStyles.Top | AnchorStyles.Bottom;
            startvaluelabel.AutoSize = true;

            txtParam.Width = 40;
            txtInterval.Width = 40;
            txtParam.Name = stepindex.ToString() + desc + "EndValue";
            txtInterval.Name = stepindex.ToString() + desc + "Interval";
            txtParam.Text = ((float)endvalue).ToString();
            txtInterval.Text = ((float)interval).ToString();

            ParameterPanel.Controls.Add(startvaluelabel, 3, row);
            ParameterPanel.Controls.Add(txtParam, 4, row);
            ParameterPanel.Controls.Add(txtInterval, 5, row);
        }

        private void StepList_DrawItem(object sender, DrawItemEventArgs e)
        {
            if (e.Index < Steps.Count)
            {
                e.DrawBackground();
                if (e.Index % 2 == 1 && (e.State & DrawItemState.Selected) != DrawItemState.Selected)
                    e.Graphics.FillRectangle(new SolidBrush(Color.LightGray), e.Bounds);
                e.Graphics.DrawString((e.Index + 1).ToString("D3") + ":", e.Font, new SolidBrush(e.ForeColor), e.Bounds);
                e.Graphics.DrawString(Steps[e.Index].GetDesc(), e.Font, new SolidBrush(e.ForeColor), new Rectangle(e.Bounds.Left + 30, e.Bounds.Top, e.Bounds.Width - 20, e.Bounds.Height));
                e.DrawFocusRectangle();
            }
        }

        private void StepList_MeasureItem(object sender, MeasureItemEventArgs e)
        {
            e.ItemHeight = (int)e.Graphics.MeasureString((e.Index + 1).ToString("D3") + ":" + Steps[e.Index].GetDesc(), StepList.Font, StepList.Width - 20).Height;
        }

        private void SaveChanges()
        {
            TextBox txtParameter;
            TextBox txtInterval;
            CheckBox chkInConstConc;
            CheckBox consttotalconc;
            ComboBox totalconc;
            for (int i = 0; i < Steps.Count; i++)
            {
                if (Steps[i].OperType == ProgStep.Operation.PrepSol)
                {
                    for (int j = 0; j < Steps[i].Comps.Count; j++)
                    {
                        txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solute + "]" + "EndValue"];
                        if (txtParameter != null)
                            ParameterEndvalues[i].Comps[j].LowConc = Convert.ToDouble(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                        txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solute + "]" + "Interval"];
                        if (txtParameter != null)
                            ParameterIntervals[i].Comps[j].LowConc = Convert.ToDouble(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                        chkInConstConc = (CheckBox)ParameterPanel.Controls[i.ToString() + "[" + Steps[i].Comps[j].Solute + "]" + "Check"];
                        if (chkInConstConc != null)
                            Steps[i].Comps[j].InConstConc = chkInConstConc.Checked;
                    }
                    consttotalconc = (CheckBox)ParameterPanel.Controls[i.ToString() + "ConstTotalConc"];
                    if (consttotalconc != null)
                        Steps[i].ConstTotalConc = consttotalconc.Checked;
                    totalconc = (ComboBox)ParameterPanel.Controls[i.ToString() + "totalConc"];
                    if (totalconc != null)
                        Steps[i].TotalConc = Convert.ToDouble(string.IsNullOrEmpty(totalconc.Text) ? "0" : totalconc.Text);
                }
                if (Steps[i].OperType == ProgStep.Operation.EChem)
                {
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "静置(秒)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["QuietTime"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].QuietTime = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "起始电位(V)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["E0"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].E0 = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "最高电位(V)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EH"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].EH = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "最低电位(V)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EL"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].EL = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "终止电位(V)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EF"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].EF = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "扫速(V/s)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["ScanRate"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].ScanRate = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "运行(秒)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["RunTime"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].RunTime = Convert.ToSingle(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);

                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "静置(秒)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["QuietTime"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].QuietTime = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "起始电位(V)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["E0"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].E0 = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "最高电位(V)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EH"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].EH = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "最低电位(V)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EL"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].EL = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "终止电位(V)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["EF"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].EF = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "扫速(V/s)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["ScanRate"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].ScanRate = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "运行(秒)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["RunTime"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].RunTime = Convert.ToSingle(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                }
                if (Steps[i].OperType == ProgStep.Operation.Blank || Steps[i].OperType == ProgStep.Operation.Flush)
                {
                    //txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + "持续(秒)" + "EndValue"];
                    txtParameter = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["DurationSec"] + "EndValue"];
                    if (txtParameter != null)
                        ParameterEndvalues[i].Duration = Convert.ToDouble(string.IsNullOrEmpty(txtParameter.Text) ? "0" : txtParameter.Text);
                    //txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + "持续(秒)" + "Interval"];
                    txtInterval = (TextBox)ParameterPanel.Controls[i.ToString() + LIB.NamedStrings["DurationSec"] + "Interval"];
                    if (txtInterval != null)
                        ParameterIntervals[i].Duration = Convert.ToDouble(string.IsNullOrEmpty(txtInterval.Text) ? "0" : txtInterval.Text);
                }
            }
        }
        private void btnSavechanges_Click(object sender, EventArgs e)
        {
            SaveChanges();
            GetExpCount(this, new EventArgs());
            List<int> constconcindex = new List<int>();
            string msgstring = "";
            constconcindex = LIB.LastExp.SetConstConcExp();
            //msgstring += "限制总浓度恒定后的实验数目为：" + constconcindex.Count.ToString() + "\r\n[";
            msgstring += LIB.NamedStrings["ConstConCmbExpCnt"] + constconcindex.Count.ToString() + "\r\n["; 
            foreach(int i in constconcindex)
            {
                msgstring += (i + 1).ToString() + ",";
            }
            msgstring = msgstring.TrimEnd(',');
            msgstring += "]";
            MsgBox.Text += msgstring;
            if (MessageBox.Show(LIB.NamedStrings["ProgramSavedandClose"], LIB.NamedStrings["Notice"], MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) == DialogResult.Yes)
                Close();
        }


        private void btnSaveRun_Click(object sender, EventArgs e)
        {
            SaveChanges();
            Close();
        }

        private void btnDisplayMatrix_Click(object sender, EventArgs e)
        {
            MsgBox.Text += LIB.LastExp.ListSelectParams();
        }

        private void btnClose_Click(object sender, EventArgs e)
        {
            Close();
        }
    }
}
