namespace eChemSDL
{
    partial class Configurations
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param Name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Configurations));
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle3 = new System.Windows.Forms.DataGridViewCellStyle();
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle4 = new System.Windows.Forms.DataGridViewCellStyle();
            this.tabChannel = new System.Windows.Forms.TabPage();
            this.ChannelGridView = new System.Windows.Forms.DataGridView();
            this.ChannelName = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.HighConc = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.TubeInnerDiameter = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.PumpSpeed = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.WheelDiameter = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.AddressDiluter = new System.Windows.Forms.DataGridViewComboBoxColumn();
            this.ChannelColor = new System.Windows.Forms.DataGridViewButtonColumn();
            this.Delete = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.tabControl = new System.Windows.Forms.TabControl();
            this.tabGeneral = new System.Windows.Forms.TabPage();
            this.tableLayoutPanel1 = new System.Windows.Forms.TableLayoutPanel();
            this.label6 = new System.Windows.Forms.Label();
            this.btnBrowse = new System.Windows.Forms.Button();
            this.cmbLanguages = new System.Windows.Forms.ComboBox();
            this.txtDataPath = new System.Windows.Forms.TextBox();
            this.label7 = new System.Windows.Forms.Label();
            this.chkStopOnError = new System.Windows.Forms.CheckBox();
            this.label24 = new System.Windows.Forms.Label();
            this.label25 = new System.Windows.Forms.Label();
            this.cmb485Port = new System.Windows.Forms.ComboBox();
            this.tabFlush = new System.Windows.Forms.TabPage();
            this.PPGridView = new System.Windows.Forms.DataGridView();
            this.Role = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.RPM = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.Direction = new System.Windows.Forms.DataGridViewComboBoxColumn();
            this.AddressFlusher = new System.Windows.Forms.DataGridViewComboBoxColumn();
            this.CycleDuration = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.label5 = new System.Windows.Forms.Label();
            this.tabPositioner = new System.Windows.Forms.TabPage();
            this.txtPickHeight = new System.Windows.Forms.TextBox();
            this.label22 = new System.Windows.Forms.Label();
            this.lblNote1 = new System.Windows.Forms.Label();
            this.pictureBox1 = new System.Windows.Forms.PictureBox();
            this.chkSameCnt = new System.Windows.Forms.CheckBox();
            this.chkSamecm = new System.Windows.Forms.CheckBox();
            this.chkSamepulse = new System.Windows.Forms.CheckBox();
            this.txtlayCnt = new System.Windows.Forms.TextBox();
            this.txtcmLay = new System.Windows.Forms.TextBox();
            this.txtpulseZ = new System.Windows.Forms.TextBox();
            this.label19 = new System.Windows.Forms.Label();
            this.label15 = new System.Windows.Forms.Label();
            this.label11 = new System.Windows.Forms.Label();
            this.txtcolCnt = new System.Windows.Forms.TextBox();
            this.txtcmCol = new System.Windows.Forms.TextBox();
            this.txtSpeed = new System.Windows.Forms.TextBox();
            this.txtpulseY = new System.Windows.Forms.TextBox();
            this.label18 = new System.Windows.Forms.Label();
            this.label14 = new System.Windows.Forms.Label();
            this.label21 = new System.Windows.Forms.Label();
            this.label20 = new System.Windows.Forms.Label();
            this.label10 = new System.Windows.Forms.Label();
            this.txtrowCnt = new System.Windows.Forms.TextBox();
            this.txtcmRow = new System.Windows.Forms.TextBox();
            this.txtpulseX = new System.Windows.Forms.TextBox();
            this.label17 = new System.Windows.Forms.Label();
            this.label13 = new System.Windows.Forms.Label();
            this.label9 = new System.Windows.Forms.Label();
            this.label23 = new System.Windows.Forms.Label();
            this.label16 = new System.Windows.Forms.Label();
            this.label12 = new System.Windows.Forms.Label();
            this.label8 = new System.Windows.Forms.Label();
            this.label3 = new System.Windows.Forms.Label();
            this.cmbPortPos = new System.Windows.Forms.ComboBox();
            this.tabDisplay = new System.Windows.Forms.TabPage();
            this.label2 = new System.Windows.Forms.Label();
            this.solvateColorview = new System.Windows.Forms.DataGridView();
            this.Solvate = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.Color = new System.Windows.Forms.DataGridViewButtonColumn();
            this.save = new System.Windows.Forms.Button();
            this.cancel = new System.Windows.Forms.Button();
            this.tabChannel.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.ChannelGridView)).BeginInit();
            this.tabControl.SuspendLayout();
            this.tabGeneral.SuspendLayout();
            this.tableLayoutPanel1.SuspendLayout();
            this.tabFlush.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.PPGridView)).BeginInit();
            this.tabPositioner.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).BeginInit();
            this.tabDisplay.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.solvateColorview)).BeginInit();
            this.SuspendLayout();
            // 
            // tabChannel
            // 
            this.tabChannel.Controls.Add(this.ChannelGridView);
            this.tabChannel.Controls.Add(this.Delete);
            this.tabChannel.Controls.Add(this.label1);
            resources.ApplyResources(this.tabChannel, "tabChannel");
            this.tabChannel.Name = "tabChannel";
            this.tabChannel.UseVisualStyleBackColor = true;
            // 
            // ChannelGridView
            // 
            this.ChannelGridView.AllowUserToResizeRows = false;
            resources.ApplyResources(this.ChannelGridView, "ChannelGridView");
            this.ChannelGridView.AutoSizeColumnsMode = System.Windows.Forms.DataGridViewAutoSizeColumnsMode.DisplayedCells;
            this.ChannelGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
            this.ChannelGridView.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.ChannelName,
            this.HighConc,
            this.TubeInnerDiameter,
            this.PumpSpeed,
            this.WheelDiameter,
            this.AddressDiluter,
            this.ChannelColor});
            this.ChannelGridView.Name = "ChannelGridView";
            this.ChannelGridView.RowTemplate.Height = 23;
            this.ChannelGridView.CellContentClick += new System.Windows.Forms.DataGridViewCellEventHandler(this.channelview_CellContentClick);
            this.ChannelGridView.DataError += new System.Windows.Forms.DataGridViewDataErrorEventHandler(this.ChannelGridView_DataError);
            this.ChannelGridView.RowPostPaint += new System.Windows.Forms.DataGridViewRowPostPaintEventHandler(this.ChannelGridView_RowPostPaint);
            // 
            // ChannelName
            // 
            this.ChannelName.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.ChannelName.DataPropertyName = "ChannelName";
            resources.ApplyResources(this.ChannelName, "ChannelName");
            this.ChannelName.Name = "ChannelName";
            this.ChannelName.Resizable = System.Windows.Forms.DataGridViewTriState.True;
            // 
            // HighConc
            // 
            this.HighConc.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.HighConc.DataPropertyName = "HighConc";
            resources.ApplyResources(this.HighConc, "HighConc");
            this.HighConc.Name = "HighConc";
            // 
            // TubeInnerDiameter
            // 
            this.TubeInnerDiameter.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.TubeInnerDiameter.DataPropertyName = "TubeInnerDiameter";
            resources.ApplyResources(this.TubeInnerDiameter, "TubeInnerDiameter");
            this.TubeInnerDiameter.Name = "TubeInnerDiameter";
            // 
            // PumpSpeed
            // 
            this.PumpSpeed.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.PumpSpeed.DataPropertyName = "PumpSpeed";
            resources.ApplyResources(this.PumpSpeed, "PumpSpeed");
            this.PumpSpeed.Name = "PumpSpeed";
            // 
            // WheelDiameter
            // 
            this.WheelDiameter.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.WheelDiameter.DataPropertyName = "WheelDiameter";
            resources.ApplyResources(this.WheelDiameter, "WheelDiameter");
            this.WheelDiameter.Name = "WheelDiameter";
            // 
            // AddressDiluter
            // 
            this.AddressDiluter.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            this.AddressDiluter.DataPropertyName = "Address";
            this.AddressDiluter.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            resources.ApplyResources(this.AddressDiluter, "AddressDiluter");
            this.AddressDiluter.Name = "AddressDiluter";
            // 
            // ChannelColor
            // 
            this.ChannelColor.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells;
            dataGridViewCellStyle3.Alignment = System.Windows.Forms.DataGridViewContentAlignment.MiddleCenter;
            dataGridViewCellStyle3.BackColor = System.Drawing.Color.Green;
            this.ChannelColor.DefaultCellStyle = dataGridViewCellStyle3;
            this.ChannelColor.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            resources.ApplyResources(this.ChannelColor, "ChannelColor");
            this.ChannelColor.Name = "ChannelColor";
            this.ChannelColor.Resizable = System.Windows.Forms.DataGridViewTriState.True;
            this.ChannelColor.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Automatic;
            // 
            // Delete
            // 
            resources.ApplyResources(this.Delete, "Delete");
            this.Delete.Name = "Delete";
            this.Delete.UseVisualStyleBackColor = true;
            this.Delete.Click += new System.EventHandler(this.Delete_Click);
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // tabControl
            // 
            resources.ApplyResources(this.tabControl, "tabControl");
            this.tabControl.Controls.Add(this.tabGeneral);
            this.tabControl.Controls.Add(this.tabChannel);
            this.tabControl.Controls.Add(this.tabFlush);
            this.tabControl.Controls.Add(this.tabPositioner);
            this.tabControl.Controls.Add(this.tabDisplay);
            this.tabControl.Name = "tabControl";
            this.tabControl.SelectedIndex = 0;
            this.tabControl.SelectedIndexChanged += new System.EventHandler(this.tabControl_SelectedIndexChanged);
            // Resource file accidentally set tabControl.Visible = false; ensure it's visible at runtime
            this.tabControl.Visible = true;
            // 
            // tabGeneral
            // 
            this.tabGeneral.Controls.Add(this.tableLayoutPanel1);
            resources.ApplyResources(this.tabGeneral, "tabGeneral");
            this.tabGeneral.Name = "tabGeneral";
            this.tabGeneral.UseVisualStyleBackColor = true;
            // 
            // tableLayoutPanel1
            // 
            resources.ApplyResources(this.tableLayoutPanel1, "tableLayoutPanel1");
            this.tableLayoutPanel1.Controls.Add(this.label6, 0, 1);
            this.tableLayoutPanel1.Controls.Add(this.btnBrowse, 2, 2);
            this.tableLayoutPanel1.Controls.Add(this.cmbLanguages, 1, 1);
            this.tableLayoutPanel1.Controls.Add(this.txtDataPath, 1, 2);
            this.tableLayoutPanel1.Controls.Add(this.label7, 0, 2);
            this.tableLayoutPanel1.Controls.Add(this.chkStopOnError, 1, 3);
            this.tableLayoutPanel1.Controls.Add(this.label24, 0, 3);
            this.tableLayoutPanel1.Controls.Add(this.label25, 0, 0);
            this.tableLayoutPanel1.Controls.Add(this.cmb485Port, 1, 0);
            this.tableLayoutPanel1.Name = "tableLayoutPanel1";
            // 
            // label6
            // 
            resources.ApplyResources(this.label6, "label6");
            this.label6.Name = "label6";
            // 
            // btnBrowse
            // 
            resources.ApplyResources(this.btnBrowse, "btnBrowse");
            this.btnBrowse.Name = "btnBrowse";
            this.btnBrowse.UseVisualStyleBackColor = true;
            this.btnBrowse.Click += new System.EventHandler(this.btnBrowse_Click);
            // 
            // cmbLanguages
            // 
            this.cmbLanguages.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbLanguages.DropDownWidth = 60;
            this.cmbLanguages.FormattingEnabled = true;
            resources.ApplyResources(this.cmbLanguages, "cmbLanguages");
            this.cmbLanguages.Name = "cmbLanguages";
            this.cmbLanguages.SelectedIndexChanged += new System.EventHandler(this.cmbLanguages_SelectedIndexChanged);
            // 
            // txtDataPath
            // 
            resources.ApplyResources(this.txtDataPath, "txtDataPath");
            this.txtDataPath.Name = "txtDataPath";
            // 
            // label7
            // 
            resources.ApplyResources(this.label7, "label7");
            this.label7.Name = "label7";
            // 
            // chkStopOnError
            // 
            resources.ApplyResources(this.chkStopOnError, "chkStopOnError");
            this.chkStopOnError.Name = "chkStopOnError";
            this.chkStopOnError.UseVisualStyleBackColor = true;
            // 
            // label24
            // 
            resources.ApplyResources(this.label24, "label24");
            this.label24.Name = "label24";
            // 
            // label25
            // 
            resources.ApplyResources(this.label25, "label25");
            this.label25.Name = "label25";
            // 
            // cmb485Port
            // 
            this.cmb485Port.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmb485Port.FormattingEnabled = true;
            resources.ApplyResources(this.cmb485Port, "cmb485Port");
            this.cmb485Port.Name = "cmb485Port";
            // 
            // tabFlush
            // 
            this.tabFlush.Controls.Add(this.PPGridView);
            this.tabFlush.Controls.Add(this.label5);
            resources.ApplyResources(this.tabFlush, "tabFlush");
            this.tabFlush.Name = "tabFlush";
            this.tabFlush.UseVisualStyleBackColor = true;
            // 
            // PPGridView
            // 
            resources.ApplyResources(this.PPGridView, "PPGridView");
            this.PPGridView.AutoSizeColumnsMode = System.Windows.Forms.DataGridViewAutoSizeColumnsMode.DisplayedCells;
            this.PPGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
            this.PPGridView.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.Role,
            this.RPM,
            this.Direction,
            this.AddressFlusher,
            this.CycleDuration});
            this.PPGridView.Name = "PPGridView";
            this.PPGridView.RowTemplate.Height = 23;
            this.PPGridView.CellFormatting += new System.Windows.Forms.DataGridViewCellFormattingEventHandler(this.PPGridView_CellFormatting);
            this.PPGridView.RowPostPaint += new System.Windows.Forms.DataGridViewRowPostPaintEventHandler(this.ChannelGridView_RowPostPaint);
            // 
            // Role
            // 
            this.Role.DataPropertyName = "PumpName";
            resources.ApplyResources(this.Role, "Role");
            this.Role.Name = "Role";
            this.Role.ReadOnly = true;
            // 
            // RPM
            // 
            this.RPM.DataPropertyName = "PumpRPM";
            resources.ApplyResources(this.RPM, "RPM");
            this.RPM.Name = "RPM";
            // 
            // Direction
            // 
            this.Direction.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            resources.ApplyResources(this.Direction, "Direction");
            this.Direction.Name = "Direction";
            this.Direction.Resizable = System.Windows.Forms.DataGridViewTriState.True;
            this.Direction.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Automatic;
            // 
            // AddressFlusher
            // 
            this.AddressFlusher.DataPropertyName = "Address";
            this.AddressFlusher.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            resources.ApplyResources(this.AddressFlusher, "AddressFlusher");
            this.AddressFlusher.Name = "AddressFlusher";
            this.AddressFlusher.Resizable = System.Windows.Forms.DataGridViewTriState.True;
            this.AddressFlusher.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Automatic;
            // 
            // CycleDuration
            // 
            this.CycleDuration.DataPropertyName = "CycleDuration";
            resources.ApplyResources(this.CycleDuration, "CycleDuration");
            this.CycleDuration.Name = "CycleDuration";
            // 
            // label5
            // 
            resources.ApplyResources(this.label5, "label5");
            this.label5.Name = "label5";
            // 
            // tabPositioner
            // 
            this.tabPositioner.Controls.Add(this.txtPickHeight);
            this.tabPositioner.Controls.Add(this.label22);
            this.tabPositioner.Controls.Add(this.lblNote1);
            this.tabPositioner.Controls.Add(this.pictureBox1);
            this.tabPositioner.Controls.Add(this.chkSameCnt);
            this.tabPositioner.Controls.Add(this.chkSamecm);
            this.tabPositioner.Controls.Add(this.chkSamepulse);
            this.tabPositioner.Controls.Add(this.txtlayCnt);
            this.tabPositioner.Controls.Add(this.txtcmLay);
            this.tabPositioner.Controls.Add(this.txtpulseZ);
            this.tabPositioner.Controls.Add(this.label19);
            this.tabPositioner.Controls.Add(this.label15);
            this.tabPositioner.Controls.Add(this.label11);
            this.tabPositioner.Controls.Add(this.txtcolCnt);
            this.tabPositioner.Controls.Add(this.txtcmCol);
            this.tabPositioner.Controls.Add(this.txtSpeed);
            this.tabPositioner.Controls.Add(this.txtpulseY);
            this.tabPositioner.Controls.Add(this.label18);
            this.tabPositioner.Controls.Add(this.label14);
            this.tabPositioner.Controls.Add(this.label21);
            this.tabPositioner.Controls.Add(this.label20);
            this.tabPositioner.Controls.Add(this.label10);
            this.tabPositioner.Controls.Add(this.txtrowCnt);
            this.tabPositioner.Controls.Add(this.txtcmRow);
            this.tabPositioner.Controls.Add(this.txtpulseX);
            this.tabPositioner.Controls.Add(this.label17);
            this.tabPositioner.Controls.Add(this.label13);
            this.tabPositioner.Controls.Add(this.label9);
            this.tabPositioner.Controls.Add(this.label23);
            this.tabPositioner.Controls.Add(this.label16);
            this.tabPositioner.Controls.Add(this.label12);
            this.tabPositioner.Controls.Add(this.label8);
            this.tabPositioner.Controls.Add(this.label3);
            this.tabPositioner.Controls.Add(this.cmbPortPos);
            resources.ApplyResources(this.tabPositioner, "tabPositioner");
            this.tabPositioner.Name = "tabPositioner";
            this.tabPositioner.UseVisualStyleBackColor = true;
            // 
            // txtPickHeight
            // 
            resources.ApplyResources(this.txtPickHeight, "txtPickHeight");
            this.txtPickHeight.Name = "txtPickHeight";
            // 
            // label22
            // 
            resources.ApplyResources(this.label22, "label22");
            this.label22.BackColor = System.Drawing.Color.White;
            this.label22.Name = "label22";
            // 
            // lblNote1
            // 
            resources.ApplyResources(this.lblNote1, "lblNote1");
            this.lblNote1.BackColor = System.Drawing.Color.White;
            this.lblNote1.Name = "lblNote1";
            // 
            // pictureBox1
            // 
            resources.ApplyResources(this.pictureBox1, "pictureBox1");
            this.pictureBox1.Name = "pictureBox1";
            this.pictureBox1.TabStop = false;
            // 
            // chkSameCnt
            // 
            resources.ApplyResources(this.chkSameCnt, "chkSameCnt");
            this.chkSameCnt.Name = "chkSameCnt";
            this.chkSameCnt.UseVisualStyleBackColor = true;
            this.chkSameCnt.CheckedChanged += new System.EventHandler(this.chkSamecm_CheckedChanged);
            // 
            // chkSamecm
            // 
            resources.ApplyResources(this.chkSamecm, "chkSamecm");
            this.chkSamecm.Name = "chkSamecm";
            this.chkSamecm.UseVisualStyleBackColor = true;
            this.chkSamecm.CheckedChanged += new System.EventHandler(this.chkSamecm_CheckedChanged);
            // 
            // chkSamepulse
            // 
            resources.ApplyResources(this.chkSamepulse, "chkSamepulse");
            this.chkSamepulse.Name = "chkSamepulse";
            this.chkSamepulse.UseVisualStyleBackColor = true;
            this.chkSamepulse.CheckedChanged += new System.EventHandler(this.chkSamepulse_CheckedChanged);
            // 
            // txtlayCnt
            // 
            resources.ApplyResources(this.txtlayCnt, "txtlayCnt");
            this.txtlayCnt.Name = "txtlayCnt";
            // 
            // txtcmLay
            // 
            resources.ApplyResources(this.txtcmLay, "txtcmLay");
            this.txtcmLay.Name = "txtcmLay";
            // 
            // txtpulseZ
            // 
            resources.ApplyResources(this.txtpulseZ, "txtpulseZ");
            this.txtpulseZ.Name = "txtpulseZ";
            // 
            // label19
            // 
            resources.ApplyResources(this.label19, "label19");
            this.label19.Name = "label19";
            // 
            // label15
            // 
            resources.ApplyResources(this.label15, "label15");
            this.label15.Name = "label15";
            // 
            // label11
            // 
            resources.ApplyResources(this.label11, "label11");
            this.label11.Name = "label11";
            // 
            // txtcolCnt
            // 
            resources.ApplyResources(this.txtcolCnt, "txtcolCnt");
            this.txtcolCnt.Name = "txtcolCnt";
            // 
            // txtcmCol
            // 
            resources.ApplyResources(this.txtcmCol, "txtcmCol");
            this.txtcmCol.Name = "txtcmCol";
            // 
            // txtSpeed
            // 
            resources.ApplyResources(this.txtSpeed, "txtSpeed");
            this.txtSpeed.Name = "txtSpeed";
            // 
            // txtpulseY
            // 
            resources.ApplyResources(this.txtpulseY, "txtpulseY");
            this.txtpulseY.Name = "txtpulseY";
            // 
            // label18
            // 
            resources.ApplyResources(this.label18, "label18");
            this.label18.Name = "label18";
            // 
            // label14
            // 
            resources.ApplyResources(this.label14, "label14");
            this.label14.Name = "label14";
            // 
            // label21
            // 
            resources.ApplyResources(this.label21, "label21");
            this.label21.Name = "label21";
            // 
            // label20
            // 
            resources.ApplyResources(this.label20, "label20");
            this.label20.Name = "label20";
            // 
            // label10
            // 
            resources.ApplyResources(this.label10, "label10");
            this.label10.Name = "label10";
            // 
            // txtrowCnt
            // 
            resources.ApplyResources(this.txtrowCnt, "txtrowCnt");
            this.txtrowCnt.Name = "txtrowCnt";
            // 
            // txtcmRow
            // 
            resources.ApplyResources(this.txtcmRow, "txtcmRow");
            this.txtcmRow.Name = "txtcmRow";
            // 
            // txtpulseX
            // 
            resources.ApplyResources(this.txtpulseX, "txtpulseX");
            this.txtpulseX.Name = "txtpulseX";
            // 
            // label17
            // 
            resources.ApplyResources(this.label17, "label17");
            this.label17.Name = "label17";
            // 
            // label13
            // 
            resources.ApplyResources(this.label13, "label13");
            this.label13.Name = "label13";
            // 
            // label9
            // 
            resources.ApplyResources(this.label9, "label9");
            this.label9.Name = "label9";
            // 
            // label23
            // 
            resources.ApplyResources(this.label23, "label23");
            this.label23.Name = "label23";
            // 
            // label16
            // 
            resources.ApplyResources(this.label16, "label16");
            this.label16.Name = "label16";
            // 
            // label12
            // 
            resources.ApplyResources(this.label12, "label12");
            this.label12.Name = "label12";
            // 
            // label8
            // 
            resources.ApplyResources(this.label8, "label8");
            this.label8.Name = "label8";
            // 
            // label3
            // 
            resources.ApplyResources(this.label3, "label3");
            this.label3.Name = "label3";
            // 
            // cmbPortPos
            // 
            this.cmbPortPos.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbPortPos.FormattingEnabled = true;
            resources.ApplyResources(this.cmbPortPos, "cmbPortPos");
            this.cmbPortPos.Name = "cmbPortPos";
            // 
            // tabDisplay
            // 
            this.tabDisplay.Controls.Add(this.label2);
            this.tabDisplay.Controls.Add(this.solvateColorview);
            resources.ApplyResources(this.tabDisplay, "tabDisplay");
            this.tabDisplay.Name = "tabDisplay";
            this.tabDisplay.UseVisualStyleBackColor = true;
            // 
            // label2
            // 
            resources.ApplyResources(this.label2, "label2");
            this.label2.Name = "label2";
            // 
            // solvateColorview
            // 
            this.solvateColorview.AllowUserToResizeRows = false;
            this.solvateColorview.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.solvateColorview.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.Solvate,
            this.Color});
            resources.ApplyResources(this.solvateColorview, "solvateColorview");
            this.solvateColorview.Name = "solvateColorview";
            this.solvateColorview.RowTemplate.Height = 23;
            // 
            // Solvate
            // 
            this.Solvate.DataPropertyName = "Solvate";
            resources.ApplyResources(this.Solvate, "Solvate");
            this.Solvate.Name = "Solvate";
            // 
            // Color
            // 
            dataGridViewCellStyle4.Alignment = System.Windows.Forms.DataGridViewContentAlignment.MiddleCenter;
            dataGridViewCellStyle4.BackColor = System.Drawing.Color.Green;
            this.Color.DefaultCellStyle = dataGridViewCellStyle4;
            this.Color.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            resources.ApplyResources(this.Color, "Color");
            this.Color.Name = "Color";
            this.Color.Resizable = System.Windows.Forms.DataGridViewTriState.True;
            this.Color.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.Automatic;
            // 
            // save
            // 
            resources.ApplyResources(this.save, "save");
            this.save.Name = "save";
            this.save.UseVisualStyleBackColor = true;
            this.save.Click += new System.EventHandler(this.save_Click);
            // 
            // cancel
            // 
            resources.ApplyResources(this.cancel, "cancel");
            this.cancel.Name = "cancel";
            this.cancel.UseVisualStyleBackColor = true;
            this.cancel.Click += new System.EventHandler(this.cancel_Click);
            // 
            // Configurations
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.cancel);
            this.Controls.Add(this.save);
            this.Controls.Add(this.tabControl);
            this.Name = "Configurations";
            this.Load += new System.EventHandler(this.Configurations_Load);
            this.tabChannel.ResumeLayout(false);
            this.tabChannel.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.ChannelGridView)).EndInit();
            this.tabControl.ResumeLayout(false);
            this.tabGeneral.ResumeLayout(false);
            this.tabGeneral.PerformLayout();
            this.tableLayoutPanel1.ResumeLayout(false);
            this.tableLayoutPanel1.PerformLayout();
            this.tabFlush.ResumeLayout(false);
            this.tabFlush.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.PPGridView)).EndInit();
            this.tabPositioner.ResumeLayout(false);
            this.tabPositioner.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).EndInit();
            this.tabDisplay.ResumeLayout(false);
            this.tabDisplay.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.solvateColorview)).EndInit();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.TabPage tabChannel;
        private System.Windows.Forms.TabControl tabControl;
        private System.Windows.Forms.Button save;
        private System.Windows.Forms.Button cancel;
        private System.Windows.Forms.Button Delete;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.DataGridView ChannelGridView;
        private System.Windows.Forms.TabPage tabDisplay;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.DataGridView solvateColorview;
        private System.Windows.Forms.TabPage tabFlush;
        private System.Windows.Forms.DataGridView PPGridView;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.TabPage tabGeneral;
        private System.Windows.Forms.Label label6;
        private System.Windows.Forms.ComboBox cmbLanguages;
        private System.Windows.Forms.TableLayoutPanel tableLayoutPanel1;
        private System.Windows.Forms.DataGridViewTextBoxColumn Solvate;
        private System.Windows.Forms.DataGridViewButtonColumn Color;
        private System.Windows.Forms.TabPage tabPositioner;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.ComboBox cmbPortPos;
        private System.Windows.Forms.TextBox txtcmLay;
        private System.Windows.Forms.TextBox txtpulseZ;
        private System.Windows.Forms.Label label15;
        private System.Windows.Forms.Label label11;
        private System.Windows.Forms.TextBox txtcmCol;
        private System.Windows.Forms.TextBox txtpulseY;
        private System.Windows.Forms.Label label14;
        private System.Windows.Forms.Label label10;
        private System.Windows.Forms.TextBox txtcmRow;
        private System.Windows.Forms.TextBox txtpulseX;
        private System.Windows.Forms.Label label13;
        private System.Windows.Forms.Label label9;
        private System.Windows.Forms.Label label12;
        private System.Windows.Forms.Label label8;
        private System.Windows.Forms.CheckBox chkSamecm;
        private System.Windows.Forms.CheckBox chkSamepulse;
        private System.Windows.Forms.TextBox txtlayCnt;
        private System.Windows.Forms.Label label19;
        private System.Windows.Forms.TextBox txtcolCnt;
        private System.Windows.Forms.Label label18;
        private System.Windows.Forms.TextBox txtrowCnt;
        private System.Windows.Forms.Label label17;
        private System.Windows.Forms.Label label16;
        private System.Windows.Forms.CheckBox chkSameCnt;
        private System.Windows.Forms.TextBox txtSpeed;
        private System.Windows.Forms.Label label21;
        private System.Windows.Forms.Label label20;
        private System.Windows.Forms.Label label22;
        private System.Windows.Forms.Label lblNote1;
        private System.Windows.Forms.PictureBox pictureBox1;
        private System.Windows.Forms.TextBox txtPickHeight;
        private System.Windows.Forms.Label label23;
        private System.Windows.Forms.Button btnBrowse;
        private System.Windows.Forms.TextBox txtDataPath;
        private System.Windows.Forms.Label label7;
        private System.Windows.Forms.CheckBox chkStopOnError;
        private System.Windows.Forms.Label label24;
        private System.Windows.Forms.Label label25;
        private System.Windows.Forms.ComboBox cmb485Port;
        private System.Windows.Forms.DataGridViewTextBoxColumn ChannelName;
        private System.Windows.Forms.DataGridViewTextBoxColumn HighConc;
        private System.Windows.Forms.DataGridViewTextBoxColumn TubeInnerDiameter;
        private System.Windows.Forms.DataGridViewTextBoxColumn PumpSpeed;
        private System.Windows.Forms.DataGridViewTextBoxColumn WheelDiameter;
        private System.Windows.Forms.DataGridViewComboBoxColumn AddressDiluter;
        private System.Windows.Forms.DataGridViewButtonColumn ChannelColor;
        private System.Windows.Forms.DataGridViewTextBoxColumn Role;
        private System.Windows.Forms.DataGridViewTextBoxColumn RPM;
        private System.Windows.Forms.DataGridViewComboBoxColumn Direction;
        private System.Windows.Forms.DataGridViewComboBoxColumn AddressFlusher;
        private System.Windows.Forms.DataGridViewTextBoxColumn CycleDuration;
    }
}