using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class ProgramEditor : Form
    {
        protected FlowLayoutPanel StepEditor = new FlowLayoutPanel();

        protected GroupBox OperationContainer = new GroupBox();
        protected FlowLayoutPanel OperationPanel = new FlowLayoutPanel();
        protected RadioButton rdbtnPrepSol = new RadioButton();
        protected RadioButton rdbtnFlush = new RadioButton();
        protected RadioButton rdbtnEChem = new RadioButton();
        protected RadioButton rdbtnTransfer = new RadioButton();
        protected RadioButton rdbtnChange = new RadioButton();
        protected RadioButton rdbtnBlank = new RadioButton();

        protected GroupBox PrepSolContainer = new GroupBox();
        protected TableLayoutPanel PrepSolPanel = new TableLayoutPanel();

        //通用电化学设置（暂时不用）
        //private FlowLayoutPanel ECSetting = new FlowLayoutPanel();
        //private GroupBox ECModecontainer = new GroupBox();
        //private GroupBox ScanModecontainer = new GroupBox();
        //private FlowLayoutPanel flpECMode = new FlowLayoutPanel();
        //private FlowLayoutPanel flpScanMode = new FlowLayoutPanel();
        //private FlowLayoutPanel flpECSetting = new FlowLayoutPanel();
        //private RadioButton rdbtnVol = new RadioButton();
        //private RadioButton rdbtnCur = new RadioButton();
        //private RadioButton rdbtnStep = new RadioButton();
        //private RadioButton rdbtnLinear = new RadioButton();
        //private RadioButton rdbtnPulse = new RadioButton();

        ////时间函数
        //private GroupBox tfcontainer = new GroupBox();
        //private TableLayoutPanel tlpTF = new TableLayoutPanel();
        //private Label lblt0 = new Label();
        //private Label lblt1 = new Label();
        //private Label lblt2 = new Label();

        //private Label lblM0 = new Label();
        //private Label lblM1 = new Label();
        //private Label lblM2 = new Label();
        //private TextBox t1 = new TextBox();
        //private TextBox t2 = new TextBox();
        //private TextBox M0 = new TextBox();
        //private TextBox M1 = new TextBox();
        //private TextBox M2 = new TextBox();
        //private ComboBox t1unit = new ComboBox();
        //private ComboBox t2unit = new ComboBox();
        //private ComboBox M0unit = new ComboBox();
        //private ComboBox M1unit = new ComboBox();
        //private ComboBox M2unit = new ComboBox();

        //持续时间
        protected GroupBox DurationContainer = new GroupBox();
        protected FlowLayoutPanel DurationPanel = new FlowLayoutPanel();
        protected Label DurationLabel = new Label();
        protected TextBox DurationValue = new TextBox();
        protected ComboBox DurationUnit = new ComboBox();

        //排空设置
        protected GroupBox EvacuateContainer = new GroupBox();
        protected FlowLayoutPanel EvacuatePanel = new FlowLayoutPanel();
        protected CheckBox EvacuateOnly = new CheckBox();
        //protected ComboBox EvacuatePumpAddr = new ComboBox();

        //移液设置
        protected GroupBox TransferContainer = new GroupBox();
        protected TableLayoutPanel TransferPanel = new TableLayoutPanel();
        protected Label PumpAddressLabel = new Label();
        protected ComboBox PumpAddress = new ComboBox();
        protected Label PumpDirectionLabel = new Label();
        protected ComboBox PumpDirection = new ComboBox();
        protected Label PumpRPMLabel = new Label();
        protected TextBox PumpRPM = new TextBox();

        //换样设置
        protected GroupBox gbxChange = new GroupBox();
        protected TableLayoutPanel tblpnlChange = new TableLayoutPanel();
        protected RadioButton rdbtnSimple = new RadioButton();
        protected RadioButton rdbtnCustom = new RadioButton();
        protected CheckBox chkPickandPlace = new CheckBox();
        protected Label lblIncX = new Label();
        protected Label lblIncY = new Label();
        protected Label lblIncZ = new Label();
        protected TextBox txtIncX = new TextBox();
        protected TextBox txtIncY = new TextBox();
        protected TextBox txtIncZ = new TextBox();

        //针对辰华电化学工作站
        protected GroupBox CHISettingContainer = new GroupBox();
        protected TableLayoutPanel CHISettingPanel = new TableLayoutPanel();
        protected Label lblTechnique = new Label();
        protected Label lblE0 = new Label();
        protected Label lblEH = new Label();
        protected Label lblEL = new Label();
        protected Label lblEF = new Label();
        protected Label lblScanrate = new Label();
        protected Label lblSensitivity = new Label();
        protected Label lblSampleInterval = new Label();
        protected Label lblScanDir = new Label();
        protected Label lblSegNum = new Label();
        protected Label lblQuietTime = new Label();
        protected Label lblRunTime = new Label();

        protected ComboBox cmbTechnique = new ComboBox();
        protected TextBox txtE0 = new TextBox();
        protected TextBox txtEH = new TextBox();
        protected TextBox txtEL = new TextBox();
        protected TextBox txtEF = new TextBox();
        protected TextBox txtScanrate = new TextBox();
        //protected TextBox txtSensitivity = new TextBox();
        protected ComboBox cmbSensitivity = new ComboBox();
        protected CheckBox chkAutosensibility = new CheckBox();
        protected TextBox txtSampleInterval = new TextBox();
        protected ComboBox cmbScanDir = new ComboBox();
        protected TextBox txtSegNum = new TextBox();
        protected TextBox txtQuietTime = new TextBox();
        protected TextBox txtRunTime = new TextBox();



        protected string[] timeunit = { "ms", "sec", "min", "hr" };
        //private string[] Vunit = { "µV", "mV", "V" };
        //private string[] Iunit = { "µA", "mA", "A" };
        protected string[] CHITechniques = { "CV", "LSV", "i-t" };
        protected string[] CVScanDir = { LIB.NamedStrings["NegScan"], LIB.NamedStrings["PosScan"] };//"负扫", "正扫" };//正扫是从低电位到高电位
        protected string[] Sensitivity = { "0.1", "0.01", "0.001", "10E-4", "10E-5", "10E-6", "10E-7", "10E-8", "10E-9", "10E-10", "10E-11", "10E-12" };

        private int selectedstep;
        public bool Saved = false;//决定了退出编辑后是否覆盖内存中现有的实验

        protected BindingList<ProgStep> Steps;


        public ProgramEditor()
        {
            InitializeComponent();
        }

        //通用电化学设置（暂时不用）
        //void controlType(object sender, EventArgs e)
        //{
        //    RadioButton rb = sender as RadioButton;

        //    if (rb == null)
        //    {
        //        MessageBox.Show("Sender is not a RadioButton");
        //        return;
        //    }

        //    if (rb.Checked)
        //    {
        //        if (rb.Text == "电压")
        //        {
        //            foreach(Control ctl in tlpTF.Controls)
        //            {
        //                if (ctl is Label && ctl.Name.Contains("lblM"))
        //                {
        //                    ctl.Text = ctl.Name.Replace("lblM","V") + " = ";
        //                }
        //                if (ctl is ComboBox && ctl.Name.Contains("M"))
        //                {
        //                    ((ComboBox)ctl).Items.Clear();
        //                    ((ComboBox)ctl).Items.AddRange(Vunit);
        //                    ((ComboBox)ctl).Text = "V";
        //                }
        //            }
        //        }
        //        if (rb.Text == "电流")
        //        {
        //            foreach (Control ctl in tlpTF.Controls)
        //            {
        //                if (ctl is Label && ctl.Name.Contains("lblM"))
        //                {
        //                    ctl.Text = ctl.Name.Replace("lblM", "I") + " = ";
        //                }
        //                if (ctl is ComboBox && ctl.Name.Contains("M"))
        //                {
        //                    ((ComboBox)ctl).Items.Clear();
        //                    ((ComboBox)ctl).Items.AddRange(Iunit);
        //                    ((ComboBox)ctl).Text = "mA";
        //                }
        //            }
        //        }
        //    }
        //}

        protected void ECTechChanged(object sender, EventArgs e)
        {
            ComboBox cmb = sender as ComboBox;
            if(cmb == null)
            {
                MessageBox.Show("Sender is not a ComboBox");
                return;
            }
            if(cmb.Text =="CV")
            {
                lblE0.Enabled = true;
                lblEH.Enabled = true;
                lblEL.Enabled = true;
                lblEF.Enabled = true;
                lblQuietTime.Enabled = true;
                lblRunTime.Enabled = false;
                lblScanDir.Enabled = true;
                lblScanrate.Enabled = true;
                lblSampleInterval.Text = LIB.NamedStrings["SamplingInterval"] + " (V)";//"采集间隔(V)";
                lblSensitivity.Text = LIB.NamedStrings["Sensitivity"] + " (V)";//"灵敏度(V)";
                lblSegNum.Enabled = true;

                txtE0.Enabled = true;
                txtEH.Enabled = true;
                txtEL.Enabled = true;
                txtEF.Enabled = true;
                txtQuietTime.Enabled = true;
                txtRunTime.Enabled = false;
                cmbScanDir.Enabled = true;
                txtScanrate.Enabled = true;
                chkAutosensibility.Enabled = true;
                txtSegNum.Enabled = true;
            }
            if(cmb.Text == "LSV")
            {
                lblE0.Enabled = true;
                lblEH.Enabled = false;
                lblEL.Enabled = false;
                lblEF.Enabled = true;
                lblQuietTime.Enabled = true;
                lblRunTime.Enabled = false;
                lblScanDir.Enabled = false;
                lblSampleInterval.Text = LIB.NamedStrings["SamplingInterval"] + " (V)";//"采集间隔(V)";
                lblSensitivity.Text = LIB.NamedStrings["Sensitivity"] + " (V)";//"灵敏度(V)";
                lblScanrate.Enabled = true;
                lblSegNum.Enabled = false;

                txtE0.Enabled = true;
                txtEH.Enabled = false;
                txtEL.Enabled = false;
                txtEF.Enabled = true;
                txtQuietTime.Enabled = true;
                txtRunTime.Enabled = false;
                cmbScanDir.Enabled = false;
                txtScanrate.Enabled = true;
                chkAutosensibility.Enabled = true;
                txtSegNum.Enabled = false;
            }
            if(cmb.Text == "i-t")
            {
                lblE0.Enabled = true;
                lblEH.Enabled = false;
                lblEL.Enabled = false;
                lblEF.Enabled = false;
                lblQuietTime.Enabled = true;
                lblRunTime.Enabled = true;
                lblScanDir.Enabled = false;
                lblScanrate.Enabled = false;
                lblSampleInterval.Text = LIB.NamedStrings["SamplingInterval"] + " (sec)";//"采集间隔(秒)";
                lblSensitivity.Text = LIB.NamedStrings["Sensitivity"] + " (A)";//"灵敏度(A)";
                lblSegNum.Enabled = false;

                txtE0.Enabled = true;
                txtEH.Enabled = false;
                txtEL.Enabled = false;
                txtEF.Enabled = false;
                txtQuietTime.Enabled = true;
                txtRunTime.Enabled = true;
                cmbScanDir.Enabled = false;
                txtScanrate.Enabled = false;
                chkAutosensibility.Enabled = false;
                txtSegNum.Enabled = false;
            }
        }

        public void OperationType(object sender, EventArgs e)
        {
            RadioButton rb = sender as RadioButton;
            Panel dummyLabel = new Panel();
            dummyLabel.Width = 0;
            dummyLabel.Height = 0;
            dummyLabel.Margin = new Padding(0, 0, 0, 0);
            Panel dummyLabel2 = new Panel();
            dummyLabel2.Width = 0;
            dummyLabel2.Height = 0;
            dummyLabel2.Margin = new Padding(0, 0, 0, 0);
            StepEditor.SuspendLayout();

            if (rb == null)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"],"Sender is not a RadioButton");
                return;
            }

            // Ensure that the RadioButton.Checked property
            // changed to true.
            if (rb.Checked)
            {
                StepEditor.Controls.Clear();
                StepEditor.Controls.Add(OperationContainer);
                StepEditor.Controls.Add(dummyLabel);
                StepEditor.SetFlowBreak(dummyLabel, true);
                
                if (rb.Name == "EChem")
                {
                    //通用电化学设置（暂时不用）
                    //StepEditor.Controls.Add(ECModecontainer);
                    //StepEditor.SetFlowBreak(ECModecontainer, true);
                    //StepEditor.Controls.Add(ScanModecontainer);
                    //StepEditor.Controls.Add(dummyLabel2);
                    //StepEditor.SetFlowBreak(dummyLabel2, true);
                    //StepEditor.Controls.Add(tfcontainer);
                    //StepEditor.SetFlowBreak(tfcontainer, true);
                    //StepEditor.Controls.Add(durcontainer);
                    //rdbtnVol.Select();
                    //rdbtnStep.Select();

                    //
                    StepEditor.Controls.Add(CHISettingContainer);
                    cmbTechnique.SelectedIndex = 0;
                }
                if(rb.Name == "PrepSol")
                {
                    StepEditor.Controls.Add(PrepSolContainer);
                }
                if (rb.Name == "Change")
                {
                    StepEditor.Controls.Add(gbxChange);
                }
                if (rb.Name == "Blank"||rb.Name == "Flush" || rb.Name == "Transfer")
                {
                    if (rb.Name == "Flush")
                    {
                        StepEditor.Controls.Add(EvacuateContainer);
                        if (EvacuateOnly.Checked)
                            DurationContainer.Enabled = false;
                        StepEditor.SetFlowBreak(EvacuateContainer, true);

                    }
                    else if (rb.Name == "Transfer")
                    {
                        StepEditor.Controls.Add(TransferContainer);
                        StepEditor.SetFlowBreak(TransferContainer, true);
                        DurationContainer.Enabled = true;
                    }
                    else
                        DurationContainer.Enabled = true;
                    StepEditor.Controls.Add(DurationContainer);
                }
            }
            StepEditor.ResumeLayout(true);
        }

        private void btnAdd_Click(object sender, EventArgs e)
        {
            ProgStep ps = new ProgStep();
            LIB.LastExp.AddStep(ps);
            //SharedComponents.LastExp.Steps.Add(ps);
            Steps.ResetBindings();
            selectedstep = StepList.SelectedIndex;
            StepList.SetSelected(StepList.Items.Count - 1, true);
        }

        //private void updatelist()
        //{
        //    StepList.Items.Clear();
        //    if (SharedComponents.LastExp.Steps.Count > 0)
        //    {
        //        int i;
        //        for (i = 0; i < SharedComponents.LastExp.Steps.Count; i++)
        //        {
        //            SharedComponents.LastExp.Steps[i].GetDesc();
        //            //StepList.Items.Add((i + 1).ToString() + "." + SharedComponents.LastExp.Steps[i].GetDesc());
        //            StepList.Items.Add(SharedComponents.LastExp.Steps[i]);
        //        }
        //        StepList.SetSelected(selectedstep, true);
        //    }
        //    else
        //    {
        //        ProgStep ps = new ProgStep();
        //        SharedComponents.LastExp.Steps.Add(ps);
        //        StepList.Items.Add(ps);
        //        StepList.SetSelected(0, true);
        //    }
        //    selectedstep = StepList.SelectedIndex;
        //}



        private void ProgramEditor_Load(object sender, EventArgs e)
        {
            
            //系统bug，需要用一个dummy对象来缩小不同控件之间的行距。
            
            Label dummyLabel = new Label();
            dummyLabel.Width = 0;
            dummyLabel.Height = 0;
            dummyLabel.Margin = new Padding(0, 0, 0, 0);

            //updatelist();0609

            if(LIB.LastExp.Steps.Count <= 0)
            {
                ProgStep ps = new ProgStep();
                LIB.LastExp.Steps.Add(ps);
            }
            Steps = new BindingList<ProgStep>(LIB.LastExp.Steps);
            StepList.DataSource = Steps;


            SuspendLayout();
            StepEditor.SuspendLayout();
            OperationPanel.SuspendLayout();
            OperationContainer.SuspendLayout();

            //选择步骤类型
            OperationContainer.Text = LIB.NamedStrings["OperType"]; // "操作类型";
            rdbtnPrepSol.Text = LIB.NamedStrings["PrepSol"];//"配液";
            rdbtnPrepSol.Name = "PrepSol";
            rdbtnEChem.Text = LIB.NamedStrings["EChem"];//"电化学";
            rdbtnEChem.Name = "EChem";
            rdbtnFlush.Text = LIB.NamedStrings["Flush"];//"冲洗";
            rdbtnFlush.Name = "Flush";
            rdbtnTransfer.Text = LIB.NamedStrings["Transfer"];
            rdbtnTransfer.Name = "Transfer";
            rdbtnChange.Text = LIB.NamedStrings["Change"];
            rdbtnChange.Name = "Change";
            rdbtnBlank.Text = LIB.NamedStrings["Blank"];// "空白";
            rdbtnBlank.Name = "Blank";
            rdbtnPrepSol.CheckedChanged += new EventHandler(OperationType);
            rdbtnFlush.CheckedChanged += new EventHandler(OperationType);
            rdbtnEChem.CheckedChanged += new EventHandler(OperationType);
            rdbtnTransfer.CheckedChanged += new EventHandler(OperationType);
            rdbtnChange.CheckedChanged += new EventHandler(OperationType);
            rdbtnBlank.CheckedChanged += new EventHandler(OperationType);
            OperationPanel.Controls.Add(rdbtnPrepSol);
            OperationPanel.Controls.Add(rdbtnEChem);
            OperationPanel.Controls.Add(rdbtnFlush);
            OperationPanel.Controls.Add(rdbtnTransfer);
            OperationPanel.Controls.Add(rdbtnChange);
            OperationPanel.Controls.Add(rdbtnBlank);
            foreach (Control ctl in OperationPanel.Controls)
                ctl.AutoSize = true;
            OperationPanel.AutoSize = true;
            OperationContainer.AutoSize = true;
            OperationPanel.Dock = DockStyle.Fill;
            OperationPanel.ResumeLayout(true);
            OperationContainer.Controls.Add(OperationPanel);
            OperationContainer.ResumeLayout(true);

            StepEditor.Controls.Add(OperationContainer);
            StepEditor.Controls.Add(dummyLabel);
            StepEditor.SetFlowBreak(dummyLabel, true);
            StepEditor.AutoSize = true;
            StepEditor.ResumeLayout(true);
            Controls.Add(StepEditor);

            //初始化成分设定表格
            PrepSolContainer.Text = LIB.NamedStrings["SolRcp"];// "溶液配方";
            PrepSolContainer.AutoSize = true;

            Label totalVollbl = new Label();
            TextBox totalVolinput = new TextBox();
            totalVollbl.Text = LIB.NamedStrings["TotalVol"];//"总体积（mL）:";
            totalVollbl.AutoSize = true;
            totalVollbl.TextAlign = ContentAlignment.MiddleLeft;
            totalVollbl.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            totalVolinput.Text = Properties.Settings.Default.TotalVol.ToString();
            totalVolinput.Name = "TotalVol";
            totalVolinput.Width = 40;

            PrepSolContainer.SuspendLayout();
            PrepSolPanel.SuspendLayout();
            Label solventlabel = new Label();
            Label orderlabel = new Label();
            solventlabel.Text = LIB.NamedStrings["Solvent"]; //"选择溶剂";
            orderlabel.Text = LIB.NamedStrings["InjectOrder"];// "注液顺序";
            solventlabel.AutoSize = true;
            orderlabel.AutoSize = true;
            PrepSolPanel.Controls.Add(solventlabel, 3, 0);
            PrepSolPanel.Controls.Add(orderlabel, 4, 0);
            for (int i = 0; i < LIB.CHs.Count; i++)
            {
                Label channellabel = new Label();
                Label lowConclabel = new Label();
                TextBox lowConcinput = new TextBox();
                RadioButton isSolvent = new RadioButton();
                ComboBox injectOrder = new ComboBox();
                //channellabel.Text = "[" + SharedComponents.CHs[i].ChannelName + "溶液,源浓度:" + "" + SharedComponents.CHs[i].HighConc.ToString() + "/L 端口:" + SharedComponents.CHs[i].PortName + "]";
                //lowConclabel.Text = "目标浓度(/L):";
                channellabel.Text = "[" + LIB.CHs[i].ChannelName + " " + LIB.NamedStrings["Source"] + " " + LIB.NamedStrings["Conc"] + ": " + LIB.CHs[i].HighConc.ToString() + "/L " + LIB.NamedStrings["Port"] + ": " + LIB.CHs[i].Address + "]";
                lowConclabel.Text = LIB.NamedStrings["LowConc"];// "目标浓度(/L):";

                lowConcinput.Text = "0";
                lowConcinput.Name = i.ToString();
                isSolvent.Name = i.ToString();
                isSolvent.AutoSize = true;
                //isSolvent.Text = "这是溶剂";
                isSolvent.CheckedChanged += IsSolvent_CheckedChanged;
                channellabel.AutoSize = true;
                lowConclabel.AutoSize = true;
                lowConcinput.Width = 40;
                channellabel.TextAlign = ContentAlignment.MiddleLeft;
                channellabel.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
                lowConclabel.TextAlign = ContentAlignment.MiddleLeft;
                lowConclabel.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
                injectOrder.Name = i.ToString();
                for (int j = 0; j < LIB.CHs.Count; j++)
                    injectOrder.Items.Add(j + 1);
                injectOrder.DropDownStyle = ComboBoxStyle.DropDownList;
                injectOrder.SelectedIndex = 0;
                injectOrder.Width = 40;

                PrepSolPanel.Controls.Add(channellabel, 0, i + 1);
                PrepSolPanel.Controls.Add(lowConclabel, 1, i + 1);
                PrepSolPanel.Controls.Add(lowConcinput, 2, i + 1);
                PrepSolPanel.Controls.Add(isSolvent, 3, i + 1);
                PrepSolPanel.Controls.Add(injectOrder, 4, i + 1);
            }
            PrepSolPanel.Controls.Add(totalVollbl, 1, LIB.CHs.Count + 1);
            PrepSolPanel.Controls.Add(totalVolinput, 2, LIB.CHs.Count + 1);
            PrepSolPanel.Dock = DockStyle.Fill;
            PrepSolPanel.AutoSize = true;
            PrepSolPanel.ResumeLayout(true);
            PrepSolContainer.Controls.Add(PrepSolPanel);
            PrepSolContainer.ResumeLayout(true);

            #region 通用电化学设置（暂时不用）
            //定义可折叠区域，也可以用Ctrl+M+H/Ctrl+M+U
            //通用电化学设置（暂时不用）
            //初始化电化学模式
            //ECModecontainer.Text = "控制输入";
            //rdbtnVol.Text = "电压";
            //rdbtnCur.Text = "电流";
            //rdbtnVol.CheckedChanged += new EventHandler(controlType);
            //rdbtnCur.CheckedChanged += new EventHandler(controlType);
            //flpECMode.Controls.Add(rdbtnVol);
            //flpECMode.Controls.Add(rdbtnCur);
            //flpECMode.AutoSize = true;
            //ECModecontainer.AutoSize = true;
            //flpECMode.Dock = DockStyle.Fill;
            //foreach (Control ctl in flpECMode.Controls)
            //    ctl.Width = 60;
            //ECModecontainer.Controls.Add(flpECMode);




            ////初始化扫描模式
            //ScanModecontainer.Text = "变化方式";
            //rdbtnStep.Text = "恒定";
            //rdbtnLinear.Text = "线性";
            //rdbtnPulse.Text = "脉冲";
            //flpScanMode.Controls.Add(rdbtnStep);
            //flpScanMode.Controls.Add(rdbtnLinear);
            //flpScanMode.Controls.Add(rdbtnPulse);
            //flpScanMode.AutoSize = true;
            //ScanModecontainer.AutoSize = true;
            //flpScanMode.Dock = DockStyle.Fill;
            //ScanModecontainer.Controls.Add(flpScanMode);
            //foreach (Control ctl in flpScanMode.Controls)
            //    ctl.Width = 60;

            ////初始化时间函数
            //tfcontainer.Text = "时间函数";
            //tfcontainer.AutoSize = true;
            //lblt0.Text = "t0 = 0";
            //lblt1.Text = "t1 = ";
            //lblt2.Text = "t2 = ";
            //lblM0.Text = "M0 = ";
            //lblM1.Text = "M1 = ";
            //lblM2.Text = "M2 = ";
            //lblM0.Name = "lblM0";
            //lblM1.Name = "lblM1";
            //lblM2.Name = "lblM2";
            //t1.Name = "t1";
            //t2.Name = "t2";
            //M0.Name = "M0";
            //M1.Name = "M1";
            //M2.Name = "M2";

            //t1unit.Name = "t1unit";
            //t2unit.Name = "t2unit";
            //M0unit.Name = "M0unit";
            //M1unit.Name = "M1unit";
            //M2unit.Name = "M2unit";

            //t1unit.Items.AddRange(timeunit);
            //t1unit.Text = "sec";
            //t2unit.Items.AddRange(timeunit);
            //t2unit.Text = "sec";

            //tlpTF.Controls.Add(lblt0, 0, 0);
            //tlpTF.Controls.Add(lblt1, 0, 1);
            //tlpTF.Controls.Add(lblt2, 0, 2);
            //tlpTF.Controls.Add(lblM0, 3, 0);
            //tlpTF.Controls.Add(lblM1, 3, 1);
            //tlpTF.Controls.Add(lblM2, 3, 2);
            //tlpTF.Controls.Add(t1, 1, 1);
            //tlpTF.Controls.Add(t2, 1, 2);
            //tlpTF.Controls.Add(M0, 4, 0);
            //tlpTF.Controls.Add(M1, 4, 1);
            //tlpTF.Controls.Add(M2, 4, 2);
            //tlpTF.Controls.Add(t1unit, 2, 1);
            //tlpTF.Controls.Add(t2unit, 2, 2);
            //tlpTF.Controls.Add(M0unit, 5, 0);
            //tlpTF.Controls.Add(M1unit, 5, 1);
            //tlpTF.Controls.Add(M2unit, 5, 2);
            //tlpTF.Dock = DockStyle.Fill;
            //foreach (Control ctl in tlpTF.Controls)
            //{

            //    if (ctl is Label)
            //    {
            //        ((Label)ctl).TextAlign = ContentAlignment.MiddleLeft;
            //        ((Label)ctl).AutoSize = true;
            //        ctl.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            //    }
            //    else
            //        ctl.Width = 60;
            //}
            //tlpTF.AutoSize = true;
            //tfcontainer.Controls.Add(tlpTF);
            #endregion

            //初始化CHI电化学工作站设置界面
            CHISettingContainer.Text = LIB.NamedStrings["ECParams"];// "设置电化学工作站";

            lblTechnique.Text = LIB.NamedStrings["Technique"];//"方法";
            lblTechnique.AutoSize = true;
            lblTechnique.TextAlign = ContentAlignment.MiddleLeft;
            lblTechnique.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            lblE0.Text = LIB.NamedStrings["E0"]; //"起始电位(V)";
            lblEH.Text = LIB.NamedStrings["EH"]; //"最高电位(V)";
            lblEL.Text = LIB.NamedStrings["EL"]; //"最低电位(V)";
            lblEF.Text = LIB.NamedStrings["EF"]; //"终止电位(V)";
            lblScanrate.Text = LIB.NamedStrings["ScanRate"]; //"扫速(V/s)";
            lblSensitivity.Text = LIB.NamedStrings["Sensitivity"];//"灵敏度(V/A)";
            chkAutosensibility.Text = LIB.NamedStrings["AutoSens"]; // "自动灵敏度 (仅在扫速低于10 mV/s时有效)";
            lblSampleInterval.Text = LIB.NamedStrings["SamplingInterval"]; // "采集间隔(V/sec)";
            lblScanDir.Text = LIB.NamedStrings["ScanDir"]; // "扫描方向";
            lblSegNum.Text = LIB.NamedStrings["SegNum"]; // "扫描段数";
            lblQuietTime.Text = LIB.NamedStrings["QuietTime"]; //"静置(秒)";
            lblRunTime.Text = LIB.NamedStrings["RunTime"]; // "运行(秒)";
            foreach(KeyValuePair<string, int> tech in ECTechs.Map)
                cmbTechnique.Items.Add(tech.Key);
            //cmbTechnique.SelectedIndex = cmbTechnique.Items.Count - 1;
            cmbTechnique.DropDownStyle = ComboBoxStyle.DropDownList;
            cmbTechnique.SelectedIndexChanged += new EventHandler(ECTechChanged);
            txtE0.Text = "0";
            txtEH.Text = "0";
            txtEL.Text = "0";
            txtEF.Text = "0";
            txtScanrate.Text = "0.1";
            cmbScanDir.DropDownStyle = ComboBoxStyle.DropDownList;
            cmbScanDir.Items.AddRange(CVScanDir);
            cmbScanDir.SelectedIndex = 1;//默认正扫
            //txtSensitivity.Text = "0.000001";
            cmbSensitivity.Items.AddRange(Sensitivity);
            cmbSensitivity.DropDownStyle = ComboBoxStyle.DropDownList;
            txtSampleInterval.Text = "0.01";
            txtSegNum.Text = "2";
            txtQuietTime.Text = "0";
            txtRunTime.Text = "0";

            CHISettingContainer.SuspendLayout();
            CHISettingPanel.SuspendLayout();
            CHISettingPanel.Controls.Add(lblTechnique, 0, 0);
            CHISettingPanel.Controls.Add(cmbTechnique, 1, 0);
            CHISettingPanel.Controls.Add(lblE0, 2, 0);
            CHISettingPanel.Controls.Add(txtE0, 3, 0);
            CHISettingPanel.Controls.Add(lblEH, 0, 1);
            CHISettingPanel.Controls.Add(txtEH, 1, 1);
            CHISettingPanel.Controls.Add(lblEL, 2, 1);
            CHISettingPanel.Controls.Add(txtEL, 3, 1);
            CHISettingPanel.Controls.Add(lblEF, 0, 2);
            CHISettingPanel.Controls.Add(txtEF, 1, 2);
            CHISettingPanel.Controls.Add(lblScanrate, 2, 2);
            CHISettingPanel.Controls.Add(txtScanrate, 3, 2);
            CHISettingPanel.Controls.Add(lblScanDir, 0, 3);
            CHISettingPanel.Controls.Add(cmbScanDir, 1, 3);
            CHISettingPanel.Controls.Add(lblSegNum, 2, 3);
            CHISettingPanel.Controls.Add(txtSegNum, 3, 3);
            CHISettingPanel.Controls.Add(lblSensitivity, 0, 4);
            //CHISettingPanel.Controls.Add(txtSensitivity, 1, 4);
            CHISettingPanel.Controls.Add(cmbSensitivity, 1, 4);
            CHISettingPanel.Controls.Add(lblSampleInterval, 2, 4);
            CHISettingPanel.Controls.Add(txtSampleInterval, 3, 4);
            CHISettingPanel.Controls.Add(chkAutosensibility, 0, 5);
            CHISettingPanel.SetColumnSpan(chkAutosensibility, 4);
            CHISettingPanel.Controls.Add(lblQuietTime, 0, 6);
            CHISettingPanel.Controls.Add(txtQuietTime, 1, 6);
            CHISettingPanel.Controls.Add(lblRunTime, 2, 6);
            CHISettingPanel.Controls.Add(txtRunTime, 3, 6);

            foreach (Control ctl in CHISettingPanel.Controls)
            {

                if (ctl is Label)
                {
                    ((Label)ctl).TextAlign = ContentAlignment.MiddleLeft;
                    ((Label)ctl).AutoSize = true;
                    ctl.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
                }
                else if (ctl is CheckBox)
                {
                    ((CheckBox)ctl).TextAlign = ContentAlignment.MiddleLeft;
                    ((CheckBox)ctl).AutoSize = true;
                    ctl.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
                }
                else
                    ctl.Width = 60;
            }
            CHISettingPanel.AutoSize = true;
            CHISettingPanel.Dock = DockStyle.Fill;
            CHISettingContainer.AutoSize = true;
            CHISettingPanel.ResumeLayout(true);
            CHISettingContainer.Controls.Add(CHISettingPanel);
            CHISettingContainer.ResumeLayout(true);

            //初始化步骤时间长度

            DurationLabel.Text = LIB.NamedStrings["Duration"]; // "持续时间：";
            DurationLabel.AutoSize = true;
            DurationLabel.TextAlign = ContentAlignment.MiddleLeft;
            DurationLabel.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            DurationValue.Width = 60;
            DurationValue.Text = "1";
            DurationUnit.Items.AddRange(timeunit);
            DurationUnit.Items.Add("cycle");
            DurationUnit.Text = "min";
            DurationUnit.Width = 60;
            DurationUnit.DropDownStyle = ComboBoxStyle.DropDownList;
            DurationPanel.AutoSize = true;
            DurationPanel.Dock = DockStyle.Fill;
            DurationPanel.SuspendLayout();
            DurationContainer.SuspendLayout();
            DurationPanel.Controls.Add(DurationLabel);
            DurationPanel.Controls.Add(DurationValue);
            DurationPanel.Controls.Add(DurationUnit);
            DurationContainer.AutoSize = true;
            DurationPanel.ResumeLayout(true);
            DurationContainer.Controls.Add(DurationPanel);
            DurationContainer.ResumeLayout(true);

            //排空设置
            EvacuateContainer.SuspendLayout();
            EvacuatePanel.SuspendLayout();
            //EvacuatePumpAddr.Anchor = AnchorStyles.Top | AnchorStyles.Left;
            EvacuateOnly.Text = LIB.NamedStrings["EvacOnly"]; // "仅排空溶液，不注水冲洗。";
            EvacuateOnly.AutoSize = true;
            EvacuateOnly.CheckedChanged += EvacuateOnly_CheckedChanged;
            //EvacuatePumpAddr.Width = 40;
            //foreach (SharedComponents.PeriPumpSettings pp in SharedComponents.PPs)
            //    EvacuatePumpAddr.Items.Add(pp.Address);
            //EvacuatePumpAddr.DropDownStyle = ComboBoxStyle.DropDownList;
            EvacuatePanel.AutoSize = true;
            EvacuatePanel.Dock = DockStyle.Fill;
            EvacuatePanel.Controls.Add(EvacuateOnly);
            //EvacuatePanel.Controls.Add(EvacuatePumpAddr);
            EvacuatePanel.ResumeLayout(true);
            EvacuateContainer.AutoSize = true;
            EvacuateContainer.Controls.Add(EvacuatePanel);
            EvacuateContainer.ResumeLayout(true);

            //移液设置
            TransferContainer.SuspendLayout();
            TransferPanel.SuspendLayout();
            PumpAddressLabel.Text = LIB.NamedStrings["PumpAddress"];
            PumpAddressLabel.AutoSize = true;
            PumpAddressLabel.TextAlign = ContentAlignment.MiddleLeft;
            PumpAddressLabel.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            foreach(LIB.PeriPumpSettings pp in LIB.PPs)
            {
                if (!PumpAddress.Items.Contains(pp.Address))
                    PumpAddress.Items.Add(pp.Address);
                PumpAddress.Sorted = true;
                PumpAddress.SelectedIndex = PumpAddress.Items.Count - 1;
            }
            PumpAddress.Width = 40;
            PumpDirectionLabel.Text = LIB.NamedStrings["Direction"];
            PumpDirectionLabel.AutoSize = true;
            PumpDirectionLabel.TextAlign = ContentAlignment.MiddleLeft;
            PumpDirectionLabel.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            PumpDirection.Items.Add(LIB.NamedStrings["forward"]);
            PumpDirection.Items.Add(LIB.NamedStrings["reverse"]);
            PumpDirection.Width = 60;
            PumpDirection.SelectedIndex = 0;
            PumpRPMLabel.Text = LIB.NamedStrings["SetSpeed"];
            PumpRPMLabel.AutoSize = true;
            PumpRPMLabel.TextAlign = ContentAlignment.MiddleLeft;
            PumpRPMLabel.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            PumpRPM.Text = "99";
            PumpRPM.Width = 40;
            //EvacuatePumpAddr.Width = 40;
            //foreach (SharedComponents.PeriPumpSettings pp in SharedComponents.PPs)
            //    EvacuatePumpAddr.Items.Add(pp.Address);
            //EvacuatePumpAddr.DropDownStyle = ComboBoxStyle.DropDownList;
            TransferPanel.AutoSize = true;
            TransferPanel.Dock = DockStyle.Fill;
            TransferPanel.Controls.Add(PumpAddressLabel, 0, 0);
            TransferPanel.Controls.Add(PumpAddress, 1, 0);
            TransferPanel.Controls.Add(PumpDirectionLabel, 0, 1);
            TransferPanel.Controls.Add(PumpDirection, 1, 1);
            TransferPanel.Controls.Add(PumpRPMLabel, 0 ,2);
            TransferPanel.Controls.Add(PumpRPM, 1, 2);

            //EvacuatePanel.Controls.Add(EvacuatePumpAddr);
            TransferPanel.ResumeLayout(true);
            TransferContainer.AutoSize = true;
            TransferContainer.Controls.Add(TransferPanel);
            TransferContainer.ResumeLayout(true);

            //换样设置
            gbxChange.Text = LIB.NamedStrings["Change"]+LIB.NamedStrings["Style"]; // "换样方式：";
            rdbtnSimple.Text = LIB.NamedStrings["Simple"];
            rdbtnSimple.AutoSize = true;
            rdbtnSimple.CheckedChanged += new EventHandler(Simple_CheckedChange);
            rdbtnSimple.Checked = true;
            rdbtnCustom.Text = LIB.NamedStrings["Custom"];
            rdbtnCustom.AutoSize = true;
            rdbtnCustom.CheckedChanged += new EventHandler(Simple_CheckedChange);
            chkPickandPlace.Text = LIB.NamedStrings["PickandPlace"];
            chkPickandPlace.AutoSize = true;
            chkPickandPlace.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            lblIncX.Text = "X轴";
            lblIncX.AutoSize = true;
            lblIncX.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            lblIncX.TextAlign = ContentAlignment.MiddleLeft;
            lblIncY.Text = "Y轴";
            lblIncY.AutoSize = true;
            lblIncY.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            lblIncY.TextAlign = ContentAlignment.MiddleLeft;
            lblIncZ.Text = "Z轴";
            lblIncZ.AutoSize = true;
            lblIncZ.TextAlign = ContentAlignment.MiddleLeft;
            lblIncZ.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Top;
            txtIncX.Text = "1";
            txtIncX.Width = 40;
            txtIncY.Text = "0";
            txtIncY.Width = 40;
            txtIncZ.Text = "0";
            txtIncZ.Width = 40;

            tblpnlChange.AutoSize = true;
            tblpnlChange.Dock = DockStyle.Fill;

            tblpnlChange.SuspendLayout();
            gbxChange.SuspendLayout();
            tblpnlChange.Controls.Add(rdbtnSimple, 0, 0);
            tblpnlChange.SetColumnSpan(rdbtnSimple, 2);
            tblpnlChange.Controls.Add(rdbtnCustom, 0, 1);
            tblpnlChange.SetColumnSpan(rdbtnCustom, 2);
            tblpnlChange.Controls.Add(chkPickandPlace, 2, 0);
            tblpnlChange.SetRowSpan(chkPickandPlace, 2);
            tblpnlChange.SetColumnSpan(chkPickandPlace, 2);
            tblpnlChange.Controls.Add(lblIncX, 0, 2);
            tblpnlChange.Controls.Add(txtIncX, 1, 2);
            tblpnlChange.Controls.Add(lblIncY, 2, 2);
            tblpnlChange.Controls.Add(txtIncY, 3, 2);
            tblpnlChange.Controls.Add(lblIncZ, 4, 2);
            tblpnlChange.Controls.Add(txtIncZ, 5, 2);
            gbxChange.AutoSize = true;
            tblpnlChange.ResumeLayout(true);
            gbxChange.Controls.Add(tblpnlChange);
            gbxChange.ResumeLayout(true);

            ResumeLayout();

            //StepList.SelectedIndex = 0;0609 // StepList.Items.Count - 1;
            LoadStepDetails();
        }

        private void Simple_CheckedChange(object sender, EventArgs e)
        {
            if(rdbtnCustom.Checked)
            {
                lblIncX.Enabled = true;
                txtIncX.Enabled = true;
                lblIncY.Enabled = true;
                txtIncY.Enabled = true;
                lblIncZ.Enabled = true;
                txtIncZ.Enabled = true;
            }
            else
            {
                lblIncX.Enabled = false;
                txtIncX.Enabled = false;
                lblIncY.Enabled = false;
                txtIncY.Enabled = false;
                lblIncZ.Enabled = false;
                txtIncZ.Enabled = false;
            }
        }

        private void EvacuateOnly_CheckedChanged(object sender, EventArgs e)
        {
            if (EvacuateOnly.Checked)
                DurationContainer.Enabled = false;
            else
                DurationContainer.Enabled = true;
        }

        private void IsSolvent_CheckedChanged(object sender, EventArgs e)
        {
            foreach (Control ctl in PrepSolPanel.Controls.Find(((RadioButton)sender).Name, true))
            {
                if (ctl is TextBox)
                {
                    if (((RadioButton)sender).Checked)
                        ctl.Enabled = false;
                    else
                        ctl.Enabled = true;
                }

            }
        }

        private void LoadStepDetails()
        {
            if (LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.PrepSol)
            {
                rdbtnPrepSol.Checked = true;
                foreach (Control ctl in PrepSolPanel.Controls)
                {
                    int index = -1;
                    if (int.TryParse(ctl.Name, out index))
                    {
                        SingleSolution lc = LIB.LastExp.Steps[StepList.SelectedIndex].Comps[index];
                        if (lc != null)
                        {
                            if (ctl is TextBox)
                            {
                                ctl.Text = lc.LowConc.ToString();
                                if (lc.IsSolvent)
                                    ctl.Enabled = false;
                            }
                            if (ctl is RadioButton)
                                if (lc.IsSolvent)
                                    ((RadioButton)ctl).Checked = true;
                            if (ctl is ComboBox)
                                ((ComboBox)ctl).SelectedItem = lc.InjectOrder + 1;
                        }
                    }
                    else if (ctl.Name == "TotalVol")
                        ctl.Text = LIB.LastExp.Steps[StepList.SelectedIndex].TotalVol.ToString();

                }
            }
            else if (LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.EChem)
            {
                rdbtnEChem.Checked = true;

                cmbTechnique.SelectedIndex = cmbTechnique.FindStringExact(LIB.LastExp.Steps[StepList.SelectedIndex].CHITechnique);
                txtE0.Text = LIB.LastExp.Steps[StepList.SelectedIndex].E0.ToString();
                txtEH.Text = LIB.LastExp.Steps[StepList.SelectedIndex].EH.ToString();
                txtEL.Text = LIB.LastExp.Steps[StepList.SelectedIndex].EL.ToString();
                txtEF.Text = LIB.LastExp.Steps[StepList.SelectedIndex].EF.ToString();
                txtScanrate.Text = LIB.LastExp.Steps[StepList.SelectedIndex].ScanRate.ToString();
                txtSegNum.Text = LIB.LastExp.Steps[StepList.SelectedIndex].SegNum.ToString();
                txtQuietTime.Text = LIB.LastExp.Steps[StepList.SelectedIndex].QuietTime.ToString();
                txtRunTime.Text = LIB.LastExp.Steps[StepList.SelectedIndex].RunTime.ToString();
                cmbScanDir.SelectedIndex = Convert.ToInt32(LIB.LastExp.Steps[StepList.SelectedIndex].ScanDir);//正扫为1/true，反扫为0/false，//TODO: 确认后直接修改界面显示字符串
                txtSampleInterval.Text = LIB.LastExp.Steps[StepList.SelectedIndex].SamplingInterval.ToString();
                //txtSensitivity.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].Sensitivity.ToString();
                int sens = Convert.ToInt32(LIB.LastExp.Steps[StepList.SelectedIndex].Sensitivity);
                cmbSensitivity.SelectedIndex = sens >= 0 ? sens : 0;
                chkAutosensibility.Checked = LIB.LastExp.Steps[StepList.SelectedIndex].AutoSensibility > 0.5F;

                //通用电化学设置（暂时不用）
                //foreach (Control ctl in flpECMode.Controls)
                //{
                //    if (SharedComponents.LastExp.Steps[StepList.SelectedIndex].ECmode == ProgStep.ECMode.V)
                //        rdbtnVol.Checked = true;
                //    else if (SharedComponents.LastExp.Steps[StepList.SelectedIndex].ECmode == ProgStep.ECMode.A)
                //        rdbtnCur.Checked = true;
                //}
                //foreach (Control ctl in flpScanMode.Controls)
                //{
                //    if (SharedComponents.LastExp.Steps[StepList.SelectedIndex].scanMode == ProgStep.ScanMode.Linear)
                //        rdbtnLinear.Checked = true;
                //    else if (SharedComponents.LastExp.Steps[StepList.SelectedIndex].scanMode == ProgStep.ScanMode.Pulse)
                //        rdbtnPulse.Checked = true;
                //    else if (SharedComponents.LastExp.Steps[StepList.SelectedIndex].scanMode == ProgStep.ScanMode.Step)
                //        rdbtnStep.Checked = true;
                //}
                //t1.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].t1.ToString();
                //t2.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].t2.ToString();
                //M0.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M0.ToString();
                //M1.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M1.ToString();
                //M2.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M2.ToString();
                //M0unit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M0unit;
                //M1unit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M1unit;
                //M2unit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].M2unit;
                //t1unit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].t1unit;
                //t2unit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].t2unit;
                //DurationValue.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].Duration.ToString();
                //DurUnit.Text = SharedComponents.LastExp.Steps[StepList.SelectedIndex].DurUnit;

            }
            else if (LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.Flush)
            {
                rdbtnFlush.Checked = true;
                DurationValue.Text = LIB.LastExp.Steps[StepList.SelectedIndex].Duration.ToString();
                DurationUnit.Text = LIB.LastExp.Steps[StepList.SelectedIndex].DurUnit;
                EvacuateOnly.Checked = LIB.LastExp.Steps[StepList.SelectedIndex].EvacuateOnly;
                //if (EvacuatePumpAddr.Items.Contains(SharedComponents.LastExp.Steps[StepList.SelectedIndex].EvacuatePump))
                //    EvacuatePumpAddr.SelectedItem = SharedComponents.LastExp.Steps[StepList.SelectedIndex].EvacuatePump;
            }
            else if (LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.Transfer)
            {
                rdbtnTransfer.Checked = true;
                DurationValue.Text = LIB.LastExp.Steps[StepList.SelectedIndex].Duration.ToString();
                DurationUnit.Text = LIB.LastExp.Steps[StepList.SelectedIndex].DurUnit;
                PumpAddress.Text = LIB.LastExp.Steps[StepList.SelectedIndex].PumpAddress.ToString();
                PumpDirection.SelectedIndex = LIB.LastExp.Steps[StepList.SelectedIndex].PumpDirection ? 0 : 1;
                PumpRPM.Text = LIB.LastExp.Steps[StepList.SelectedIndex].PumpRPM.ToString();
            }
            else if(LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.Change)
            {
                rdbtnChange.Checked = true;
                rdbtnSimple.Checked = LIB.LastExp.Steps[StepList.SelectedIndex].SimpleChange;
                rdbtnCustom.Checked = !LIB.LastExp.Steps[StepList.SelectedIndex].SimpleChange;
                chkPickandPlace.Checked = LIB.LastExp.Steps[StepList.SelectedIndex].PickandPlace;
                txtIncX.Text = LIB.LastExp.Steps[StepList.SelectedIndex].IncX.ToString();
                txtIncY.Text = LIB.LastExp.Steps[StepList.SelectedIndex].IncY.ToString();
                txtIncZ.Text = LIB.LastExp.Steps[StepList.SelectedIndex].IncZ.ToString();
            }
            else if (LIB.LastExp.Steps[StepList.SelectedIndex].OperType == ProgStep.Operation.Blank)
            {
                rdbtnBlank.Checked = true;
                DurationValue.Text = LIB.LastExp.Steps[StepList.SelectedIndex].Duration.ToString();
                DurationUnit.Text = LIB.LastExp.Steps[StepList.SelectedIndex].DurUnit;
            }
        }

        private void SaveStepDetails()
        {
            if (rdbtnPrepSol.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.PrepSol;
                LIB.LastExp.Steps[selectedstep].Comps.Clear();
                SingleSolution lc;
                foreach (Control ctl in PrepSolPanel.Controls)
                {
                    if (ctl.Name == "TotalVol")
                        LIB.LastExp.Steps[selectedstep].TotalVol = Convert.ToDouble(ctl.Text);
                    else if (ctl is TextBox)
                    {
                        int index = -1;
                        if (int.TryParse(ctl.Name, out index))
                        {
                            if (!string.IsNullOrEmpty(ctl.Text))
                                lc = new SingleSolution(index, Convert.ToDouble(ctl.Text), false);
                            else
                                lc = new SingleSolution(index, 0.0, false);
                            LIB.LastExp.Steps[selectedstep].Comps.Add(lc);
                        }
                    }
                }
                //上面这个循环先添加组分，下面循环再对组分赋值
                foreach (Control ctl in PrepSolPanel.Controls)
                {
                    int index = -1;
                    if (int.TryParse(ctl.Name, out index))
                    {
                        if (ctl is RadioButton)
                        {
                            if (((RadioButton)ctl).Checked)
                            {
                                //Solvent = ctl.Name;
                                LIB.LastExp.Steps[selectedstep].Comps[Convert.ToInt32(ctl.Name)].IsSolvent = true;
                            }
                        }
                        else if (ctl is ComboBox)
                            LIB.LastExp.Steps[selectedstep].Comps[Convert.ToInt32(ctl.Name)].InjectOrder = (int)((ComboBox)ctl).SelectedItem - 1;
                    }

                }
            }

            else if (rdbtnEChem.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.EChem;

                LIB.LastExp.Steps[selectedstep].CHITechnique = cmbTechnique.GetItemText(cmbTechnique.SelectedItem);
                LIB.LastExp.Steps[selectedstep].E0 = Convert.ToSingle(string.IsNullOrEmpty(txtE0.Text)? "0": txtE0.Text);
                LIB.LastExp.Steps[selectedstep].EH = Convert.ToSingle(string.IsNullOrEmpty(txtEH.Text) ? "0" : txtEH.Text);
                LIB.LastExp.Steps[selectedstep].EL = Convert.ToSingle(string.IsNullOrEmpty(txtEL.Text) ? "0" : txtEL.Text);
                LIB.LastExp.Steps[selectedstep].EF = Convert.ToSingle(string.IsNullOrEmpty(txtEF.Text) ? "0" : txtEF.Text);
                LIB.LastExp.Steps[selectedstep].ScanRate = Convert.ToSingle(string.IsNullOrEmpty(txtScanrate.Text) ? "0.1" : txtScanrate.Text);
                LIB.LastExp.Steps[selectedstep].SegNum = Convert.ToSingle(string.IsNullOrEmpty(txtSegNum.Text) ? "2" : txtSegNum.Text);
                LIB.LastExp.Steps[selectedstep].QuietTime = Convert.ToSingle(string.IsNullOrEmpty(txtQuietTime.Text) ? "0" : txtQuietTime.Text);
                LIB.LastExp.Steps[selectedstep].RunTime = Convert.ToSingle(string.IsNullOrEmpty(txtRunTime.Text) ? "0" : txtRunTime.Text);
                LIB.LastExp.Steps[selectedstep].ScanDir = Convert.ToSingle(cmbScanDir.SelectedIndex);//0是负扫，1是正扫
                LIB.LastExp.Steps[selectedstep].AutoSensibility = Convert.ToSingle(chkAutosensibility.Checked);
                //SharedComponents.LastExp.Steps[selectedstep].Sensitivity = Convert.ToSingle(string.IsNullOrEmpty(txtSensitivity.Text) ? "0.000001" : txtSensitivity.Text);
                LIB.LastExp.Steps[selectedstep].Sensitivity = Convert.ToSingle(cmbSensitivity.SelectedIndex);
                LIB.LastExp.Steps[selectedstep].SamplingInterval = Convert.ToSingle(string.IsNullOrEmpty(txtSampleInterval.Text) ? "0.01" : txtSampleInterval.Text);
                //通用电化学设置（暂时不用）
                //foreach (Control ctl in flpECMode.Controls)
                //{
                //    if (rdbtnVol.Checked)
                //        SharedComponents.LastExp.Steps[selectedstep].ECmode = ProgStep.ECMode.V;
                //    else if (rdbtnCur.Checked)
                //        SharedComponents.LastExp.Steps[selectedstep].ECmode = ProgStep.ECMode.A;
                //}
                //foreach (Control ctl in flpScanMode.Controls)
                //{
                //    if (rdbtnLinear.Checked)
                //        SharedComponents.LastExp.Steps[selectedstep].scanMode = ProgStep.ScanMode.Linear;
                //    else if (rdbtnPulse.Checked)
                //        SharedComponents.LastExp.Steps[selectedstep].scanMode = ProgStep.ScanMode.Pulse;
                //    else if (rdbtnStep.Checked)
                //        SharedComponents.LastExp.Steps[selectedstep].scanMode = ProgStep.ScanMode.Step;
                //}
                //SharedComponents.LastExp.Steps[selectedstep].t1 = Convert.ToDouble(string.IsNullOrEmpty(t1.Text) ? "0" : t1.Text);
                //SharedComponents.LastExp.Steps[selectedstep].t2 = Convert.ToDouble(string.IsNullOrEmpty(t2.Text) ? "0" : t2.Text);
                //SharedComponents.LastExp.Steps[selectedstep].M0 = Convert.ToDouble(string.IsNullOrEmpty(M0.Text) ? "0" : M0.Text);
                //SharedComponents.LastExp.Steps[selectedstep].M1 = Convert.ToDouble(string.IsNullOrEmpty(M1.Text) ? "0" : M1.Text);
                //SharedComponents.LastExp.Steps[selectedstep].M2 = Convert.ToDouble(string.IsNullOrEmpty(M2.Text) ? "0" : M2.Text);
                //SharedComponents.LastExp.Steps[selectedstep].t1unit = t1unit.Text;
                //SharedComponents.LastExp.Steps[selectedstep].t2unit = t2unit.Text;
                //SharedComponents.LastExp.Steps[selectedstep].M0unit = M0unit.Text;
                //SharedComponents.LastExp.Steps[selectedstep].M1unit = M1unit.Text;
                //SharedComponents.LastExp.Steps[selectedstep].M2unit = M2unit.Text;
                //SharedComponents.LastExp.Steps[selectedstep].Duration = Convert.ToDouble(string.IsNullOrEmpty(DurationValue.Text) ? "0" : DurationValue.Text);
                //SharedComponents.LastExp.Steps[selectedstep].DurUnit = DurUnit.Text;
            }
            else if (rdbtnFlush.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.Flush;
                LIB.LastExp.Steps[selectedstep].Duration = Convert.ToDouble(string.IsNullOrEmpty(DurationValue.Text) ? "0" : DurationValue.Text);
                LIB.LastExp.Steps[selectedstep].DurUnit = DurationUnit.Text;
                LIB.LastExp.Steps[selectedstep].EvacuateOnly = EvacuateOnly.Checked;
                //SharedComponents.LastExp.Steps[selectedstep].EvacuatePump = Convert.ToInt32(string.IsNullOrEmpty(EvacuatePumpAddr.Text) ? "0" : EvacuatePumpAddr.Text);
            }
            else if (rdbtnTransfer.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.Transfer;
                LIB.LastExp.Steps[selectedstep].Duration = Convert.ToDouble(string.IsNullOrEmpty(DurationValue.Text) ? "0" : DurationValue.Text);
                LIB.LastExp.Steps[selectedstep].DurUnit = DurationUnit.Text;
                LIB.LastExp.Steps[selectedstep].PumpAddress = Convert.ToByte(string.IsNullOrEmpty(PumpAddress.Text) ? LIB.PPs.SingleOrDefault(pp => pp.PumpName == "Transfer").Address.ToString() : PumpAddress.Text);
                LIB.LastExp.Steps[selectedstep].PumpDirection = PumpDirection.SelectedIndex == 0;
                LIB.LastExp.Steps[selectedstep].PumpRPM = Convert.ToUInt16(string.IsNullOrEmpty(PumpRPM.Text) ? "99" : PumpRPM.Text);
                //SharedComponents.LastExp.Steps[selectedstep].EvacuatePump = Convert.ToInt32(string.IsNullOrEmpty(EvacuatePumpAddr.Text) ? "0" : EvacuatePumpAddr.Text);
            }
            else if(rdbtnChange.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.Change;
                LIB.LastExp.Steps[selectedstep].SimpleChange = rdbtnSimple.Checked;
                LIB.LastExp.Steps[selectedstep].PickandPlace = chkPickandPlace.Checked;
                LIB.LastExp.Steps[selectedstep].IncX = Convert.ToInt32(string.IsNullOrEmpty(txtIncX.Text) ? "1" : txtIncX.Text);
                LIB.LastExp.Steps[selectedstep].IncY = Convert.ToInt32(string.IsNullOrEmpty(txtIncY.Text) ? "1" : txtIncY.Text);
                LIB.LastExp.Steps[selectedstep].IncZ = Convert.ToInt32(string.IsNullOrEmpty(txtIncZ.Text) ? "1" : txtIncZ.Text);
            }
            else if (rdbtnBlank.Checked)
            {
                LIB.LastExp.Steps[selectedstep].OperType = ProgStep.Operation.Blank;
                LIB.LastExp.Steps[selectedstep].Duration = Convert.ToDouble(string.IsNullOrEmpty(DurationValue.Text) ? "0" : DurationValue.Text);
                LIB.LastExp.Steps[selectedstep].DurUnit = DurationUnit.Text;
            }
            Steps.ResetBindings();
            LIB.LastExp.UpdateStep(selectedstep);
        }


        private void stepList_MeasureItem(object sender, MeasureItemEventArgs e)
        {
            e.ItemHeight = (int)e.Graphics.MeasureString((e.Index + 1).ToString("D3") + ":" + LIB.LastExp.Steps[e.Index].GetDesc(), StepList.Font, StepList.Width - 20).Height;
        }

        private void stepList_DrawItem(object sender, DrawItemEventArgs e)
        {
            if(e.Index<LIB.LastExp.Steps.Count)
            {
                e.DrawBackground();
                if (e.Index % 2 == 1 && (e.State & DrawItemState.Selected) != DrawItemState.Selected)
                    e.Graphics.FillRectangle(new SolidBrush(Color.LightGray), e.Bounds);
                e.Graphics.DrawString((e.Index + 1).ToString("D3") + ":", e.Font, new SolidBrush(e.ForeColor), e.Bounds);
                e.Graphics.DrawString(LIB.LastExp.Steps[e.Index].GetDesc(), e.Font, new SolidBrush(e.ForeColor), new Rectangle(e.Bounds.Left + 30, e.Bounds.Top, e.Bounds.Width - 20, e.Bounds.Height));
                e.DrawFocusRectangle();

            }
        }

        private void btnDelete_Click(object sender, EventArgs e)
        {
            if (StepList.SelectedIndex >= 0)
            {
                selectedstep = StepList.SelectedIndex;
                if (LIB.LastExp.Steps.Count > 1)
                {
                    //SharedComponents.LastExp.Steps.RemoveAt(selectedstep);
                    LIB.LastExp.DeleteStep(selectedstep);
                    if(selectedstep > 0)
                        selectedstep--;
                    StepList.SelectedIndex = selectedstep;
                    //string Json;
                    //Json = JsonConvert.SerializeObject(SharedComponents.LastExp.Steps);
                    //MessageBox.Show(Json);
                    Steps.ResetBindings();
                    LoadStepDetails();//必须保证左边显示的步骤是删除后的上一步骤，否则一更新反而把删掉的步骤存回程序了
                    //Json = selectedstep.ToString();
                    //MessageBox.Show(Json);
                }
            }
        }


        private void stepList_SelectedIndexChanged(object sender, EventArgs e)
        {
            ListBox lb = (ListBox)sender;
            if (selectedstep != StepList.SelectedIndex) //不能更新当前选择的步骤（重复点击），否则崩溃
//            if (lb.Focused && selectedstep != StepList.SelectedIndex) //不能更新当前选择的步骤（重复点击），否则崩溃
            {
                SaveStepDetails();
                selectedstep = StepList.SelectedIndex;
                LoadStepDetails();
            }
        }

        private void btnUp_Click(object sender, EventArgs e)
        {
            if(StepList.SelectedIndex >0)
            {
                selectedstep = StepList.SelectedIndex;
                ProgStep psTemp = LIB.LastExp.Steps[selectedstep];//TODO:这里可能有问题，只是引用，不是实际
                LIB.LastExp.DeleteStep(selectedstep);
                LIB.LastExp.InsertStep(selectedstep - 1, psTemp);
                //SharedComponents.LastExp.Steps.RemoveAt(selectedstep);
                //SharedComponents.LastExp.Steps.Insert(selectedstep - 1, psTemp);
                Steps.ResetBindings();
                if(selectedstep > 0)
                    selectedstep--;
                StepList.SelectedIndex = selectedstep;
            }
        }

        private void btnDown_Click(object sender, EventArgs e)
        {
            if (StepList.SelectedIndex < (StepList.Items.Count - 1))
            {
                selectedstep = StepList.SelectedIndex;
                ProgStep psTemp = LIB.LastExp.Steps[selectedstep];
                LIB.LastExp.DeleteStep(selectedstep);
                LIB.LastExp.InsertStep(selectedstep + 1, psTemp);
                //SharedComponents.LastExp.Steps.RemoveAt(selectedstep);
                //SharedComponents.LastExp.Steps.Insert(selectedstep + 1, psTemp);
                Steps.ResetBindings();
                selectedstep++;
                StepList.SelectedIndex = selectedstep;
            }

        }

        private void btnRun_Click(object sender, EventArgs e)
        {
            SaveStepDetails();
            Close();
        }

        private void btnClose_Click(object sender, EventArgs e)
        {
            Close();
        }

        private void btnSaveProgram_Click(object sender, EventArgs e)
        {
            SaveStepDetails();
            if (MessageBox.Show(LIB.NamedStrings["ProgramSavedandClose"], LIB.NamedStrings["Notice"], MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) == DialogResult.Yes)
                Close();
        }
    }
}
