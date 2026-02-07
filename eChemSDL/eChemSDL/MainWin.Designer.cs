namespace eChemSDL
{
    partial class MainWin
    {
        /// <summary>
        /// 必需的设计器变量。
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// 清理所有正在使用的资源。
        /// </summary>
        /// <param Name="disposing">如果应释放托管资源，为 true；否则为 false。</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows 窗体设计器生成的代码

        /// <summary>
        /// 设计器支持所需的方法 - 不要修改
        /// 使用代码编辑器修改此方法的内容。
        /// </summary>
        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(MainWin));
            System.Windows.Forms.DataVisualization.Charting.ChartArea chartArea1 = new System.Windows.Forms.DataVisualization.Charting.ChartArea();
            System.Windows.Forms.DataVisualization.Charting.Series series1 = new System.Windows.Forms.DataVisualization.Charting.Series();
            this.BottomToolStripPanel = new System.Windows.Forms.ToolStripPanel();
            this.TopToolStripPanel = new System.Windows.Forms.ToolStripPanel();
            this.RightToolStripPanel = new System.Windows.Forms.ToolStripPanel();
            this.LeftToolStripPanel = new System.Windows.Forms.ToolStripPanel();
            this.ContentPanel = new System.Windows.Forms.ToolStripContentPanel();
            this.menuStrip1 = new System.Windows.Forms.MenuStrip();
            this.文件FToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.SingleExpToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.CombExpToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.LoadtoolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.SaveToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripMenuItem1 = new System.Windows.Forms.ToolStripSeparator();
            this.ExitToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.帮助HToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.关于HTPSolutionToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.工具TToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.SettingToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.CalibrateToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.ManualToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.注射泵ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.rS485蠕动泵ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.三轴平台ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStripMenuItem2 = new System.Windows.Forms.ToolStripMenuItem();
            this.针筒排气ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.电化学ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.测试用ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.MenuItem_Settings = new System.Windows.Forms.ToolStripMenuItem();
            this.form1ToolStripMenuItem = new System.Windows.Forms.ToolStripMenuItem();
            this.toolStrip1 = new System.Windows.Forms.ToolStrip();
            this.toolStripBtnSingleExp = new System.Windows.Forms.ToolStripButton();
            this.toolStripBtnComboExp = new System.Windows.Forms.ToolStripButton();
            this.toolStripBtnLoadExp = new System.Windows.Forms.ToolStripButton();
            this.toolStripBtnSaveExp = new System.Windows.Forms.ToolStripButton();
            this.toolStripSeparator1 = new System.Windows.Forms.ToolStripSeparator();
            this.toolStripBtnMakeSol = new System.Windows.Forms.ToolStripButton();
            this.toolStripBtnConfig = new System.Windows.Forms.ToolStripButton();
            this.toolStripBtnCalibrate = new System.Windows.Forms.ToolStripButton();
            this.toolStripButton1 = new System.Windows.Forms.ToolStripButton();
            this.tableLayoutPanel1 = new System.Windows.Forms.TableLayoutPanel();
            this.stepProgress = new System.Windows.Forms.ListBox();
            this.LogMsgbox = new System.Windows.Forms.RichTextBox();
            this.flowLayoutPanel1 = new System.Windows.Forms.FlowLayoutPanel();
            this.btnRunSingleExp = new System.Windows.Forms.Button();
            this.btnRunComboExp = new System.Windows.Forms.Button();
            this.btnStopstep = new System.Windows.Forms.Button();
            this.btnPrevCombo = new System.Windows.Forms.Button();
            this.btnNextCombo = new System.Windows.Forms.Button();
            this.btnJumptoCombo = new System.Windows.Forms.Button();
            this.btnResetCombo = new System.Windows.Forms.Button();
            this.btnDisplayMatrix = new System.Windows.Forms.Button();
            this.VAChart = new System.Windows.Forms.DataVisualization.Charting.Chart();
            this.toolTip1 = new System.Windows.Forms.ToolTip(this.components);
            this.statusStrip1 = new System.Windows.Forms.StatusStrip();
            this.tsRS485 = new System.Windows.Forms.ToolStripStatusLabel();
            this.tsCHI = new System.Windows.Forms.ToolStripStatusLabel();
            this.tsPositioner = new System.Windows.Forms.ToolStripStatusLabel();
            this.menuStrip1.SuspendLayout();
            this.toolStrip1.SuspendLayout();
            this.tableLayoutPanel1.SuspendLayout();
            this.flowLayoutPanel1.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.VAChart)).BeginInit();
            this.SuspendLayout();
            // 
            // BottomToolStripPanel
            // 
            resources.ApplyResources(this.BottomToolStripPanel, "BottomToolStripPanel");
            this.BottomToolStripPanel.Name = "BottomToolStripPanel";
            this.BottomToolStripPanel.Orientation = System.Windows.Forms.Orientation.Horizontal;
            this.BottomToolStripPanel.RowMargin = new System.Windows.Forms.Padding(3, 0, 0, 0);
            // 
            // TopToolStripPanel
            // 
            resources.ApplyResources(this.TopToolStripPanel, "TopToolStripPanel");
            this.TopToolStripPanel.Name = "TopToolStripPanel";
            this.TopToolStripPanel.Orientation = System.Windows.Forms.Orientation.Horizontal;
            this.TopToolStripPanel.RowMargin = new System.Windows.Forms.Padding(3, 0, 0, 0);
            // 
            // RightToolStripPanel
            // 
            resources.ApplyResources(this.RightToolStripPanel, "RightToolStripPanel");
            this.RightToolStripPanel.Name = "RightToolStripPanel";
            this.RightToolStripPanel.Orientation = System.Windows.Forms.Orientation.Horizontal;
            this.RightToolStripPanel.RowMargin = new System.Windows.Forms.Padding(3, 0, 0, 0);
            // 
            // LeftToolStripPanel
            // 
            resources.ApplyResources(this.LeftToolStripPanel, "LeftToolStripPanel");
            this.LeftToolStripPanel.Name = "LeftToolStripPanel";
            this.LeftToolStripPanel.Orientation = System.Windows.Forms.Orientation.Horizontal;
            this.LeftToolStripPanel.RowMargin = new System.Windows.Forms.Padding(3, 0, 0, 0);
            // 
            // ContentPanel
            // 
            resources.ApplyResources(this.ContentPanel, "ContentPanel");
            // 
            // menuStrip1
            // 
            this.menuStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.文件FToolStripMenuItem,
            this.帮助HToolStripMenuItem,
            this.工具TToolStripMenuItem,
            this.测试用ToolStripMenuItem});
            resources.ApplyResources(this.menuStrip1, "menuStrip1");
            this.menuStrip1.Name = "menuStrip1";
            // 
            // 文件FToolStripMenuItem
            // 
            this.文件FToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.SingleExpToolStripMenuItem,
            this.CombExpToolStripMenuItem,
            this.LoadtoolStripMenuItem,
            this.SaveToolStripMenuItem,
            this.toolStripMenuItem1,
            this.ExitToolStripMenuItem});
            this.文件FToolStripMenuItem.Name = "文件FToolStripMenuItem";
            resources.ApplyResources(this.文件FToolStripMenuItem, "文件FToolStripMenuItem");
            // 
            // SingleExpToolStripMenuItem
            // 
            this.SingleExpToolStripMenuItem.Name = "SingleExpToolStripMenuItem";
            resources.ApplyResources(this.SingleExpToolStripMenuItem, "SingleExpToolStripMenuItem");
            this.SingleExpToolStripMenuItem.Click += new System.EventHandler(this.SingleExperiment_ToolStripMenuItem_Click);
            // 
            // CombExpToolStripMenuItem
            // 
            this.CombExpToolStripMenuItem.Name = "CombExpToolStripMenuItem";
            resources.ApplyResources(this.CombExpToolStripMenuItem, "CombExpToolStripMenuItem");
            this.CombExpToolStripMenuItem.Click += new System.EventHandler(this.CombExpToolStripMenuItem_Click);
            // 
            // LoadtoolStripMenuItem
            // 
            this.LoadtoolStripMenuItem.Name = "LoadtoolStripMenuItem";
            resources.ApplyResources(this.LoadtoolStripMenuItem, "LoadtoolStripMenuItem");
            this.LoadtoolStripMenuItem.Click += new System.EventHandler(this.LoadtoolStripMenuItem_Click);
            // 
            // SaveToolStripMenuItem
            // 
            this.SaveToolStripMenuItem.Name = "SaveToolStripMenuItem";
            resources.ApplyResources(this.SaveToolStripMenuItem, "SaveToolStripMenuItem");
            this.SaveToolStripMenuItem.Click += new System.EventHandler(this.SaveToolStripMenuItem_Click);
            // 
            // toolStripMenuItem1
            // 
            this.toolStripMenuItem1.Name = "toolStripMenuItem1";
            resources.ApplyResources(this.toolStripMenuItem1, "toolStripMenuItem1");
            // 
            // ExitToolStripMenuItem
            // 
            this.ExitToolStripMenuItem.Name = "ExitToolStripMenuItem";
            resources.ApplyResources(this.ExitToolStripMenuItem, "ExitToolStripMenuItem");
            this.ExitToolStripMenuItem.Click += new System.EventHandler(this.ExitToolStripMenuItem_Click);
            // 
            // 帮助HToolStripMenuItem
            // 
            this.帮助HToolStripMenuItem.Alignment = System.Windows.Forms.ToolStripItemAlignment.Right;
            this.帮助HToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.关于HTPSolutionToolStripMenuItem});
            this.帮助HToolStripMenuItem.Name = "帮助HToolStripMenuItem";
            resources.ApplyResources(this.帮助HToolStripMenuItem, "帮助HToolStripMenuItem");
            // 
            // 关于HTPSolutionToolStripMenuItem
            // 
            this.关于HTPSolutionToolStripMenuItem.Name = "关于HTPSolutionToolStripMenuItem";
            resources.ApplyResources(this.关于HTPSolutionToolStripMenuItem, "关于HTPSolutionToolStripMenuItem");
            this.关于HTPSolutionToolStripMenuItem.Click += new System.EventHandler(this.AboutHTPSolutionToolStripMenuItem_Click);
            // 
            // 工具TToolStripMenuItem
            // 
            this.工具TToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.SettingToolStripMenuItem,
            this.CalibrateToolStripMenuItem,
            this.ManualToolStripMenuItem,
            this.toolStripMenuItem2,
            this.针筒排气ToolStripMenuItem,
            this.电化学ToolStripMenuItem});
            this.工具TToolStripMenuItem.Name = "工具TToolStripMenuItem";
            resources.ApplyResources(this.工具TToolStripMenuItem, "工具TToolStripMenuItem");
            // 
            // SettingToolStripMenuItem
            // 
            this.SettingToolStripMenuItem.Name = "SettingToolStripMenuItem";
            resources.ApplyResources(this.SettingToolStripMenuItem, "SettingToolStripMenuItem");
            this.SettingToolStripMenuItem.Click += new System.EventHandler(this.ConfToolStripMenuItem_Click);
            // 
            // CalibrateToolStripMenuItem
            // 
            this.CalibrateToolStripMenuItem.Name = "CalibrateToolStripMenuItem";
            resources.ApplyResources(this.CalibrateToolStripMenuItem, "CalibrateToolStripMenuItem");
            this.CalibrateToolStripMenuItem.Click += new System.EventHandler(this.CalibrateToolStripMenuItem_Click);
            // 
            // ManualToolStripMenuItem
            // 
            this.ManualToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.注射泵ToolStripMenuItem,
            this.rS485蠕动泵ToolStripMenuItem,
            this.三轴平台ToolStripMenuItem});
            this.ManualToolStripMenuItem.Name = "ManualToolStripMenuItem";
            resources.ApplyResources(this.ManualToolStripMenuItem, "ManualToolStripMenuItem");
            // 
            // 注射泵ToolStripMenuItem
            // 
            this.注射泵ToolStripMenuItem.Name = "注射泵ToolStripMenuItem";
            resources.ApplyResources(this.注射泵ToolStripMenuItem, "注射泵ToolStripMenuItem");
            this.注射泵ToolStripMenuItem.Click += new System.EventHandler(this.注射泵ToolStripMenuItem_Click);
            // 
            // rS485蠕动泵ToolStripMenuItem
            // 
            this.rS485蠕动泵ToolStripMenuItem.Name = "rS485蠕动泵ToolStripMenuItem";
            resources.ApplyResources(this.rS485蠕动泵ToolStripMenuItem, "rS485蠕动泵ToolStripMenuItem");
            this.rS485蠕动泵ToolStripMenuItem.Click += new System.EventHandler(this.rS485蠕动泵ToolStripMenuItem_Click);
            // 
            // 三轴平台ToolStripMenuItem
            // 
            this.三轴平台ToolStripMenuItem.Name = "三轴平台ToolStripMenuItem";
            resources.ApplyResources(this.三轴平台ToolStripMenuItem, "三轴平台ToolStripMenuItem");
            this.三轴平台ToolStripMenuItem.Click += new System.EventHandler(this.三轴平台ToolStripMenuItem_Click);
            // 
            // toolStripMenuItem2
            // 
            this.toolStripMenuItem2.Name = "toolStripMenuItem2";
            resources.ApplyResources(this.toolStripMenuItem2, "toolStripMenuItem2");
            this.toolStripMenuItem2.Click += new System.EventHandler(this.PrepSolToolStripMenuItem_Click);
            // 
            // 针筒排气ToolStripMenuItem
            // 
            this.针筒排气ToolStripMenuItem.Name = "针筒排气ToolStripMenuItem";
            resources.ApplyResources(this.针筒排气ToolStripMenuItem, "针筒排气ToolStripMenuItem");
            this.针筒排气ToolStripMenuItem.Click += new System.EventHandler(this.针筒排气ToolStripMenuItem_Click);
            // 
            // 电化学ToolStripMenuItem
            // 
            this.电化学ToolStripMenuItem.Name = "电化学ToolStripMenuItem";
            resources.ApplyResources(this.电化学ToolStripMenuItem, "电化学ToolStripMenuItem");
            this.电化学ToolStripMenuItem.Click += new System.EventHandler(this.电化学ToolStripMenuItem_Click);
            // 
            // 测试用ToolStripMenuItem
            // 
            this.测试用ToolStripMenuItem.DropDownItems.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.MenuItem_Settings,
            this.form1ToolStripMenuItem});
            this.测试用ToolStripMenuItem.Name = "测试用ToolStripMenuItem";
            resources.ApplyResources(this.测试用ToolStripMenuItem, "测试用ToolStripMenuItem");
            // 
            // MenuItem_Settings
            // 
            this.MenuItem_Settings.Name = "MenuItem_Settings";
            resources.ApplyResources(this.MenuItem_Settings, "MenuItem_Settings");
            this.MenuItem_Settings.Click += new System.EventHandler(this.测试用ToolStripMenuItem_Click);
            // 
            // form1ToolStripMenuItem
            // 
            this.form1ToolStripMenuItem.Name = "form1ToolStripMenuItem";
            resources.ApplyResources(this.form1ToolStripMenuItem, "form1ToolStripMenuItem");
            this.form1ToolStripMenuItem.Click += new System.EventHandler(this.form1ToolStripMenuItem_Click);
            // 
            // toolStrip1
            // 
            this.toolStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.toolStripBtnSingleExp,
            this.toolStripBtnComboExp,
            this.toolStripBtnLoadExp,
            this.toolStripBtnSaveExp,
            this.toolStripSeparator1,
            this.toolStripBtnMakeSol,
            this.toolStripBtnConfig,
            this.toolStripBtnCalibrate,
            this.toolStripButton1});
            resources.ApplyResources(this.toolStrip1, "toolStrip1");
            this.toolStrip1.Name = "toolStrip1";
            // 
            // toolStripBtnSingleExp
            // 
            this.toolStripBtnSingleExp.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnSingleExp, "toolStripBtnSingleExp");
            this.toolStripBtnSingleExp.Name = "toolStripBtnSingleExp";
            this.toolStripBtnSingleExp.Click += new System.EventHandler(this.SingleExperiment_ToolStripMenuItem_Click);
            // 
            // toolStripBtnComboExp
            // 
            this.toolStripBtnComboExp.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnComboExp, "toolStripBtnComboExp");
            this.toolStripBtnComboExp.Name = "toolStripBtnComboExp";
            this.toolStripBtnComboExp.Click += new System.EventHandler(this.CombExpToolStripMenuItem_Click);
            // 
            // toolStripBtnLoadExp
            // 
            this.toolStripBtnLoadExp.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnLoadExp, "toolStripBtnLoadExp");
            this.toolStripBtnLoadExp.Name = "toolStripBtnLoadExp";
            this.toolStripBtnLoadExp.Click += new System.EventHandler(this.LoadtoolStripMenuItem_Click);
            // 
            // toolStripBtnSaveExp
            // 
            this.toolStripBtnSaveExp.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnSaveExp, "toolStripBtnSaveExp");
            this.toolStripBtnSaveExp.Name = "toolStripBtnSaveExp";
            this.toolStripBtnSaveExp.Click += new System.EventHandler(this.SaveToolStripMenuItem_Click);
            // 
            // toolStripSeparator1
            // 
            this.toolStripSeparator1.Name = "toolStripSeparator1";
            resources.ApplyResources(this.toolStripSeparator1, "toolStripSeparator1");
            // 
            // toolStripBtnMakeSol
            // 
            this.toolStripBtnMakeSol.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnMakeSol, "toolStripBtnMakeSol");
            this.toolStripBtnMakeSol.Name = "toolStripBtnMakeSol";
            this.toolStripBtnMakeSol.Click += new System.EventHandler(this.PrepSolToolStripMenuItem_Click);
            // 
            // toolStripBtnConfig
            // 
            this.toolStripBtnConfig.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnConfig, "toolStripBtnConfig");
            this.toolStripBtnConfig.Name = "toolStripBtnConfig";
            this.toolStripBtnConfig.Click += new System.EventHandler(this.ConfToolStripMenuItem_Click);
            // 
            // toolStripBtnCalibrate
            // 
            this.toolStripBtnCalibrate.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripBtnCalibrate, "toolStripBtnCalibrate");
            this.toolStripBtnCalibrate.Name = "toolStripBtnCalibrate";
            this.toolStripBtnCalibrate.Click += new System.EventHandler(this.CalibrateToolStripMenuItem_Click);
            // 
            // toolStripButton1
            // 
            this.toolStripButton1.DisplayStyle = System.Windows.Forms.ToolStripItemDisplayStyle.Image;
            resources.ApplyResources(this.toolStripButton1, "toolStripButton1");
            this.toolStripButton1.Name = "toolStripButton1";
            // 
            // tableLayoutPanel1
            // 
            resources.ApplyResources(this.tableLayoutPanel1, "tableLayoutPanel1");
            this.tableLayoutPanel1.Controls.Add(this.stepProgress, 0, 0);
            this.tableLayoutPanel1.Controls.Add(this.LogMsgbox, 1, 0);
            this.tableLayoutPanel1.Controls.Add(this.flowLayoutPanel1, 0, 1);
            this.tableLayoutPanel1.Name = "tableLayoutPanel1";
            // 
            // stepProgress
            // 
            resources.ApplyResources(this.stepProgress, "stepProgress");
            this.stepProgress.DrawMode = System.Windows.Forms.DrawMode.OwnerDrawVariable;
            this.stepProgress.FormattingEnabled = true;
            this.stepProgress.Name = "stepProgress";
            this.stepProgress.DrawItem += new System.Windows.Forms.DrawItemEventHandler(this.stepProgress_DrawItem);
            this.stepProgress.MeasureItem += new System.Windows.Forms.MeasureItemEventHandler(this.stepProgress_MeasureItem);
            this.stepProgress.DataSourceChanged += new System.EventHandler(this.stepProgress_DataSourceChanged);
            // 
            // LogMsgbox
            // 
            this.LogMsgbox.BackColor = System.Drawing.SystemColors.InactiveBorder;
            resources.ApplyResources(this.LogMsgbox, "LogMsgbox");
            this.LogMsgbox.ForeColor = System.Drawing.Color.DarkGreen;
            this.LogMsgbox.Name = "LogMsgbox";
            this.LogMsgbox.ReadOnly = true;
            this.tableLayoutPanel1.SetRowSpan(this.LogMsgbox, 2);
            // 
            // flowLayoutPanel1
            // 
            resources.ApplyResources(this.flowLayoutPanel1, "flowLayoutPanel1");
            this.flowLayoutPanel1.Controls.Add(this.btnRunSingleExp);
            this.flowLayoutPanel1.Controls.Add(this.btnRunComboExp);
            this.flowLayoutPanel1.Controls.Add(this.btnStopstep);
            this.flowLayoutPanel1.Controls.Add(this.btnPrevCombo);
            this.flowLayoutPanel1.Controls.Add(this.btnNextCombo);
            this.flowLayoutPanel1.Controls.Add(this.btnJumptoCombo);
            this.flowLayoutPanel1.Controls.Add(this.btnResetCombo);
            this.flowLayoutPanel1.Controls.Add(this.btnDisplayMatrix);
            this.flowLayoutPanel1.Name = "flowLayoutPanel1";
            // 
            // btnRunSingleExp
            // 
            resources.ApplyResources(this.btnRunSingleExp, "btnRunSingleExp");
            this.btnRunSingleExp.Name = "btnRunSingleExp";
            this.btnRunSingleExp.TabStop = false;
            this.toolTip1.SetToolTip(this.btnRunSingleExp, resources.GetString("btnRunSingleExp.ToolTip"));
            this.btnRunSingleExp.UseVisualStyleBackColor = true;
            this.btnRunSingleExp.Click += new System.EventHandler(this.btnRunSingleExp_Click);
            // 
            // btnRunComboExp
            // 
            resources.ApplyResources(this.btnRunComboExp, "btnRunComboExp");
            this.btnRunComboExp.Name = "btnRunComboExp";
            this.toolTip1.SetToolTip(this.btnRunComboExp, resources.GetString("btnRunComboExp.ToolTip"));
            this.btnRunComboExp.UseVisualStyleBackColor = true;
            this.btnRunComboExp.Click += new System.EventHandler(this.btnRunComboExp_Click);
            // 
            // btnStopstep
            // 
            resources.ApplyResources(this.btnStopstep, "btnStopstep");
            this.btnStopstep.Name = "btnStopstep";
            this.toolTip1.SetToolTip(this.btnStopstep, resources.GetString("btnStopstep.ToolTip"));
            this.btnStopstep.UseVisualStyleBackColor = true;
            this.btnStopstep.Click += new System.EventHandler(this.btnStopstep_Click);
            // 
            // btnPrevCombo
            // 
            resources.ApplyResources(this.btnPrevCombo, "btnPrevCombo");
            this.btnPrevCombo.Name = "btnPrevCombo";
            this.toolTip1.SetToolTip(this.btnPrevCombo, resources.GetString("btnPrevCombo.ToolTip"));
            this.btnPrevCombo.UseVisualStyleBackColor = true;
            this.btnPrevCombo.Click += new System.EventHandler(this.btnPrevCombo_Click);
            // 
            // btnNextCombo
            // 
            resources.ApplyResources(this.btnNextCombo, "btnNextCombo");
            this.btnNextCombo.Name = "btnNextCombo";
            this.toolTip1.SetToolTip(this.btnNextCombo, resources.GetString("btnNextCombo.ToolTip"));
            this.btnNextCombo.UseVisualStyleBackColor = true;
            this.btnNextCombo.Click += new System.EventHandler(this.btnNextCombo_Click);
            // 
            // btnJumptoCombo
            // 
            resources.ApplyResources(this.btnJumptoCombo, "btnJumptoCombo");
            this.btnJumptoCombo.Name = "btnJumptoCombo";
            this.toolTip1.SetToolTip(this.btnJumptoCombo, resources.GetString("btnJumptoCombo.ToolTip"));
            this.btnJumptoCombo.UseVisualStyleBackColor = true;
            this.btnJumptoCombo.Click += new System.EventHandler(this.btnJumptoCombo_Click);
            // 
            // btnResetCombo
            // 
            resources.ApplyResources(this.btnResetCombo, "btnResetCombo");
            this.btnResetCombo.Name = "btnResetCombo";
            this.toolTip1.SetToolTip(this.btnResetCombo, resources.GetString("btnResetCombo.ToolTip"));
            this.btnResetCombo.UseVisualStyleBackColor = true;
            this.btnResetCombo.Click += new System.EventHandler(this.btnResetCombop_Click);
            // 
            // btnDisplayMatrix
            // 
            resources.ApplyResources(this.btnDisplayMatrix, "btnDisplayMatrix");
            this.btnDisplayMatrix.Name = "btnDisplayMatrix";
            this.btnDisplayMatrix.UseVisualStyleBackColor = true;
            this.btnDisplayMatrix.Click += new System.EventHandler(this.btnDisplayMatrix_Click);
            // 
            // VAChart
            // 
            this.VAChart.BackColor = System.Drawing.Color.Silver;
            this.VAChart.BorderlineColor = System.Drawing.Color.DimGray;
            this.VAChart.BorderSkin.BorderDashStyle = System.Windows.Forms.DataVisualization.Charting.ChartDashStyle.Solid;
            this.VAChart.BorderSkin.PageColor = System.Drawing.Color.Transparent;
            this.VAChart.BorderSkin.SkinStyle = System.Windows.Forms.DataVisualization.Charting.BorderSkinStyle.FrameThin6;
            chartArea1.AlignmentOrientation = ((System.Windows.Forms.DataVisualization.Charting.AreaAlignmentOrientations)((System.Windows.Forms.DataVisualization.Charting.AreaAlignmentOrientations.Vertical | System.Windows.Forms.DataVisualization.Charting.AreaAlignmentOrientations.Horizontal)));
            chartArea1.AxisX.IsStartedFromZero = false;
            chartArea1.AxisX.LabelStyle.Enabled = false;
            chartArea1.AxisX.MajorGrid.LineColor = System.Drawing.Color.LightGray;
            chartArea1.AxisX.MajorTickMark.TickMarkStyle = System.Windows.Forms.DataVisualization.Charting.TickMarkStyle.InsideArea;
            chartArea1.AxisY.IsStartedFromZero = false;
            chartArea1.AxisY.LabelStyle.Enabled = false;
            chartArea1.AxisY.MajorGrid.LineColor = System.Drawing.Color.LightGray;
            chartArea1.AxisY.MajorTickMark.TickMarkStyle = System.Windows.Forms.DataVisualization.Charting.TickMarkStyle.InsideArea;
            chartArea1.BackColor = System.Drawing.Color.White;
            chartArea1.BorderColor = System.Drawing.Color.DimGray;
            chartArea1.BorderDashStyle = System.Windows.Forms.DataVisualization.Charting.ChartDashStyle.Solid;
            chartArea1.BorderWidth = 2;
            chartArea1.Name = "ChartArea";
            chartArea1.Position.Auto = false;
            chartArea1.Position.Height = 72F;
            chartArea1.Position.Width = 72F;
            chartArea1.Position.X = 12F;
            chartArea1.Position.Y = 12F;
            this.VAChart.ChartAreas.Add(chartArea1);
            resources.ApplyResources(this.VAChart, "VAChart");
            this.VAChart.Name = "VAChart";
            this.VAChart.Palette = System.Windows.Forms.DataVisualization.Charting.ChartColorPalette.Bright;
            series1.ChartArea = "ChartArea";
            series1.ChartType = System.Windows.Forms.DataVisualization.Charting.SeriesChartType.FastLine;
            series1.IsVisibleInLegend = false;
            series1.Name = "CHIData";
            series1.XValueMember = "X";
            series1.YValueMembers = "Y";
            this.VAChart.Series.Add(series1);
            // 
            // statusStrip1
            // 
            this.statusStrip1.Items.AddRange(new System.Windows.Forms.ToolStripItem[] {
            this.tsRS485,
            this.tsCHI,
            this.tsPositioner});
            this.statusStrip1.Name = "statusStrip1";
            resources.ApplyResources(this.statusStrip1, "statusStrip1");
            // 
            // tsRS485
            // 
            this.tsRS485.Name = "tsRS485";
            this.tsRS485.Text = "RS485: Unknown";
            // 
            // tsCHI
            // 
            this.tsCHI.Name = "tsCHI";
            this.tsCHI.Text = "CHI: Unknown";
            // 
            // tsPositioner
            // 
            this.tsPositioner.Name = "tsPositioner";
            this.tsPositioner.Text = "Positioner: Unknown";

            // Add statusStrip to controls (ensure it's at bottom)
            this.Controls.Add(this.statusStrip1);

            // 
            // MainWin
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.BackColor = System.Drawing.SystemColors.Window;
            this.Controls.Add(this.VAChart);
            this.Controls.Add(this.tableLayoutPanel1);
            this.Controls.Add(this.toolStrip1);
            this.Controls.Add(this.menuStrip1);
            this.DoubleBuffered = true;
            this.MainMenuStrip = this.menuStrip1;
            this.Name = "MainWin";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.MainWin_FormClosing);
            this.Load += new System.EventHandler(this.MainWin_Load);
            this.Paint += new System.Windows.Forms.PaintEventHandler(this.MainWin_Paint);
            this.Enter += new System.EventHandler(this.MainWin_Enter);
            this.menuStrip1.ResumeLayout(false);
            this.menuStrip1.PerformLayout();
            this.toolStrip1.ResumeLayout(false);
            this.toolStrip1.PerformLayout();
            this.tableLayoutPanel1.ResumeLayout(false);
            this.flowLayoutPanel1.ResumeLayout(false);
            this.flowLayoutPanel1.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.VAChart)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.ToolStripPanel BottomToolStripPanel;
        private System.Windows.Forms.ToolStripPanel TopToolStripPanel;
        private System.Windows.Forms.ToolStripPanel RightToolStripPanel;
        private System.Windows.Forms.ToolStripPanel LeftToolStripPanel;
        private System.Windows.Forms.ToolStripContentPanel ContentPanel;
        private System.Windows.Forms.MenuStrip menuStrip1;
        private System.Windows.Forms.ToolStripMenuItem 文件FToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem SingleExpToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem LoadtoolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem SaveToolStripMenuItem;
        private System.Windows.Forms.ToolStripSeparator toolStripMenuItem1;
        private System.Windows.Forms.ToolStripMenuItem ExitToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem 帮助HToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem 关于HTPSolutionToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem 工具TToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem SettingToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem CalibrateToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem ManualToolStripMenuItem;
        private System.Windows.Forms.ToolStrip toolStrip1;
        private System.Windows.Forms.ToolStripButton toolStripBtnSingleExp;
        private System.Windows.Forms.ToolStripMenuItem toolStripMenuItem2;
        private System.Windows.Forms.ToolStripMenuItem 测试用ToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem 针筒排气ToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem CombExpToolStripMenuItem;
        private System.Windows.Forms.TableLayoutPanel tableLayoutPanel1;
        private System.Windows.Forms.ListBox stepProgress;
        private System.Windows.Forms.FlowLayoutPanel flowLayoutPanel1;
        private System.Windows.Forms.Button btnPrevCombo;
        private System.Windows.Forms.Button btnStopstep;
        private System.Windows.Forms.Button btnRunSingleExp;
        private System.Windows.Forms.Button btnNextCombo;
        private System.Windows.Forms.Button btnResetCombo;
        private System.Windows.Forms.ToolStripMenuItem 电化学ToolStripMenuItem;
        private System.Windows.Forms.ToolStripButton toolStripBtnComboExp;
        private System.Windows.Forms.ToolStripSeparator toolStripSeparator1;
        private System.Windows.Forms.ToolStripButton toolStripBtnMakeSol;
        private System.Windows.Forms.ToolStripButton toolStripBtnLoadExp;
        private System.Windows.Forms.ToolStripButton toolStripBtnSaveExp;
        private System.Windows.Forms.ToolStripButton toolStripBtnConfig;
        private System.Windows.Forms.ToolStripButton toolStripBtnCalibrate;
        private System.Windows.Forms.ToolStripMenuItem 注射泵ToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem rS485蠕动泵ToolStripMenuItem;
        private System.Windows.Forms.DataVisualization.Charting.Chart VAChart;
        private System.Windows.Forms.RichTextBox LogMsgbox;
        private System.Windows.Forms.Button btnRunComboExp;
        private System.Windows.Forms.ToolTip toolTip1;
        private System.Windows.Forms.Button btnDisplayMatrix;
        private System.Windows.Forms.ToolStripButton toolStripButton1;
        private System.Windows.Forms.ToolStripMenuItem MenuItem_Settings;
        private System.Windows.Forms.Button btnJumptoCombo;
        private System.Windows.Forms.ToolStripMenuItem 三轴平台ToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem form1ToolStripMenuItem;
        // status strip members
        private System.Windows.Forms.StatusStrip statusStrip1;
        private System.Windows.Forms.ToolStripStatusLabel tsRS485;
        private System.Windows.Forms.ToolStripStatusLabel tsCHI;
        private System.Windows.Forms.ToolStripStatusLabel tsPositioner;
    }
}

