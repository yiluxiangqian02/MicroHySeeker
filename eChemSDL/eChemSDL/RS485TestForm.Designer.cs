namespace eChemSDL
{
    partial class RS485调试
    {
        /// <summary>
        /// 必需的设计器变量。
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// 清理所有正在使用的资源。
        /// </summary>
        /// <param name="disposing">如果应释放托管资源，为 true；否则为 false。</param>
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
            this.F1_groupBox1_连接设置 = new System.Windows.Forms.GroupBox();
            this.GB1_comboBox_通讯地址 = new System.Windows.Forms.ComboBox();
            this.GB1_label_通讯地址 = new System.Windows.Forms.Label();
            this.F1_groupBox6_数据日志 = new System.Windows.Forms.GroupBox();
            this.GB6_textBox_数据日志 = new System.Windows.Forms.TextBox();
            this.GB4_groupBox3_电机速度控制模式 = new System.Windows.Forms.GroupBox();
            this.GB4_3_panel_正转or反转 = new System.Windows.Forms.Panel();
            this.GB4_3_radioButton_反转 = new System.Windows.Forms.RadioButton();
            this.GB4_3_radioButton_正转 = new System.Windows.Forms.RadioButton();
            this.GB4_3_button_关闭上电自动运行 = new System.Windows.Forms.Button();
            this.GB4_3_button_开启上电自动运行 = new System.Windows.Forms.Button();
            this.GB4_3_button_停止 = new System.Windows.Forms.Button();
            this.GB4_3_button_开始 = new System.Windows.Forms.Button();
            this.GB4_3_comboBox_速度档位 = new System.Windows.Forms.ComboBox();
            this.GB4_3_label_提示 = new System.Windows.Forms.Label();
            this.GB4_3_label_速度档位 = new System.Windows.Forms.Label();
            this.GB4_groupBox4_电机位置控制模式 = new System.Windows.Forms.GroupBox();
            this.GB4_4_panel_正转or反转 = new System.Windows.Forms.Panel();
            this.GB4_4_radioButton_反转 = new System.Windows.Forms.RadioButton();
            this.GB4_4_radioButton_正转 = new System.Windows.Forms.RadioButton();
            this.GB4_4_button_停止 = new System.Windows.Forms.Button();
            this.GB4_4_button_开始 = new System.Windows.Forms.Button();
            this.GB4_4_label_提示 = new System.Windows.Forms.Label();
            this.GB4_4_textBox_脉冲数 = new System.Windows.Forms.TextBox();
            this.GB4_4_comboBox_速度档位 = new System.Windows.Forms.ComboBox();
            this.GB4_4_comboBox_模式切换 = new System.Windows.Forms.ComboBox();
            this.GB4_4_label_脉冲数 = new System.Windows.Forms.Label();
            this.GB4_4_label_速度档位 = new System.Windows.Forms.Label();
            this.serialPort1 = new System.IO.Ports.SerialPort(this.components);
            this.btnReadversion = new System.Windows.Forms.Button();
            this.btnReadSetting = new System.Windows.Forms.Button();
            this.btnReadStatus = new System.Windows.Forms.Button();
            this.btnRunstate = new System.Windows.Forms.Button();
            this.F1_groupBox1_连接设置.SuspendLayout();
            this.F1_groupBox6_数据日志.SuspendLayout();
            this.GB4_groupBox3_电机速度控制模式.SuspendLayout();
            this.GB4_3_panel_正转or反转.SuspendLayout();
            this.GB4_groupBox4_电机位置控制模式.SuspendLayout();
            this.GB4_4_panel_正转or反转.SuspendLayout();
            this.SuspendLayout();
            // 
            // F1_groupBox1_连接设置
            // 
            this.F1_groupBox1_连接设置.BackColor = System.Drawing.SystemColors.Control;
            this.F1_groupBox1_连接设置.BackgroundImageLayout = System.Windows.Forms.ImageLayout.None;
            this.F1_groupBox1_连接设置.Controls.Add(this.GB1_comboBox_通讯地址);
            this.F1_groupBox1_连接设置.Controls.Add(this.GB1_label_通讯地址);
            this.F1_groupBox1_连接设置.Font = new System.Drawing.Font("宋体", 11F);
            this.F1_groupBox1_连接设置.Location = new System.Drawing.Point(12, 12);
            this.F1_groupBox1_连接设置.Name = "F1_groupBox1_连接设置";
            this.F1_groupBox1_连接设置.Size = new System.Drawing.Size(301, 62);
            this.F1_groupBox1_连接设置.TabIndex = 8;
            this.F1_groupBox1_连接设置.TabStop = false;
            this.F1_groupBox1_连接设置.Text = "连接设置";
            // 
            // GB1_comboBox_通讯地址
            // 
            this.GB1_comboBox_通讯地址.FormattingEnabled = true;
            this.GB1_comboBox_通讯地址.Location = new System.Drawing.Point(77, 23);
            this.GB1_comboBox_通讯地址.Name = "GB1_comboBox_通讯地址";
            this.GB1_comboBox_通讯地址.Size = new System.Drawing.Size(97, 23);
            this.GB1_comboBox_通讯地址.TabIndex = 3;
            // 
            // GB1_label_通讯地址
            // 
            this.GB1_label_通讯地址.AutoSize = true;
            this.GB1_label_通讯地址.Font = new System.Drawing.Font("宋体", 10F);
            this.GB1_label_通讯地址.Location = new System.Drawing.Point(10, 27);
            this.GB1_label_通讯地址.Name = "GB1_label_通讯地址";
            this.GB1_label_通讯地址.Size = new System.Drawing.Size(63, 14);
            this.GB1_label_通讯地址.TabIndex = 6;
            this.GB1_label_通讯地址.Text = "通讯地址";
            // 
            // F1_groupBox6_数据日志
            // 
            this.F1_groupBox6_数据日志.BackColor = System.Drawing.SystemColors.Control;
            this.F1_groupBox6_数据日志.Controls.Add(this.GB6_textBox_数据日志);
            this.F1_groupBox6_数据日志.Font = new System.Drawing.Font("宋体", 11F);
            this.F1_groupBox6_数据日志.Location = new System.Drawing.Point(12, 84);
            this.F1_groupBox6_数据日志.Name = "F1_groupBox6_数据日志";
            this.F1_groupBox6_数据日志.Size = new System.Drawing.Size(301, 369);
            this.F1_groupBox6_数据日志.TabIndex = 13;
            this.F1_groupBox6_数据日志.TabStop = false;
            this.F1_groupBox6_数据日志.Text = "数据日志";
            // 
            // GB6_textBox_数据日志
            // 
            this.GB6_textBox_数据日志.BackColor = System.Drawing.SystemColors.Menu;
            this.GB6_textBox_数据日志.Font = new System.Drawing.Font("宋体", 10F);
            this.GB6_textBox_数据日志.Location = new System.Drawing.Point(12, 23);
            this.GB6_textBox_数据日志.Multiline = true;
            this.GB6_textBox_数据日志.Name = "GB6_textBox_数据日志";
            this.GB6_textBox_数据日志.ReadOnly = true;
            this.GB6_textBox_数据日志.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.GB6_textBox_数据日志.Size = new System.Drawing.Size(289, 340);
            this.GB6_textBox_数据日志.TabIndex = 0;
            this.GB6_textBox_数据日志.Tag = "1";
            // 
            // GB4_groupBox3_电机速度控制模式
            // 
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_panel_正转or反转);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_button_关闭上电自动运行);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_button_开启上电自动运行);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_button_停止);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_button_开始);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_comboBox_速度档位);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_label_提示);
            this.GB4_groupBox3_电机速度控制模式.Controls.Add(this.GB4_3_label_速度档位);
            this.GB4_groupBox3_电机速度控制模式.Location = new System.Drawing.Point(334, 12);
            this.GB4_groupBox3_电机速度控制模式.Name = "GB4_groupBox3_电机速度控制模式";
            this.GB4_groupBox3_电机速度控制模式.Size = new System.Drawing.Size(278, 229);
            this.GB4_groupBox3_电机速度控制模式.TabIndex = 14;
            this.GB4_groupBox3_电机速度控制模式.TabStop = false;
            this.GB4_groupBox3_电机速度控制模式.Text = "电机速度控制模式";
            // 
            // GB4_3_panel_正转or反转
            // 
            this.GB4_3_panel_正转or反转.Controls.Add(this.GB4_3_radioButton_反转);
            this.GB4_3_panel_正转or反转.Controls.Add(this.GB4_3_radioButton_正转);
            this.GB4_3_panel_正转or反转.Location = new System.Drawing.Point(38, 28);
            this.GB4_3_panel_正转or反转.Name = "GB4_3_panel_正转or反转";
            this.GB4_3_panel_正转or反转.Size = new System.Drawing.Size(225, 34);
            this.GB4_3_panel_正转or反转.TabIndex = 0;
            // 
            // GB4_3_radioButton_反转
            // 
            this.GB4_3_radioButton_反转.AutoSize = true;
            this.GB4_3_radioButton_反转.Location = new System.Drawing.Point(131, 9);
            this.GB4_3_radioButton_反转.Name = "GB4_3_radioButton_反转";
            this.GB4_3_radioButton_反转.Size = new System.Drawing.Size(47, 16);
            this.GB4_3_radioButton_反转.TabIndex = 0;
            this.GB4_3_radioButton_反转.TabStop = true;
            this.GB4_3_radioButton_反转.Tag = "";
            this.GB4_3_radioButton_反转.Text = "反转";
            this.GB4_3_radioButton_反转.UseVisualStyleBackColor = true;
            // 
            // GB4_3_radioButton_正转
            // 
            this.GB4_3_radioButton_正转.AutoSize = true;
            this.GB4_3_radioButton_正转.Location = new System.Drawing.Point(13, 9);
            this.GB4_3_radioButton_正转.Name = "GB4_3_radioButton_正转";
            this.GB4_3_radioButton_正转.Size = new System.Drawing.Size(47, 16);
            this.GB4_3_radioButton_正转.TabIndex = 1;
            this.GB4_3_radioButton_正转.TabStop = true;
            this.GB4_3_radioButton_正转.Tag = "";
            this.GB4_3_radioButton_正转.Text = "正转";
            this.GB4_3_radioButton_正转.UseVisualStyleBackColor = true;
            // 
            // GB4_3_button_关闭上电自动运行
            // 
            this.GB4_3_button_关闭上电自动运行.Location = new System.Drawing.Point(15, 192);
            this.GB4_3_button_关闭上电自动运行.Name = "GB4_3_button_关闭上电自动运行";
            this.GB4_3_button_关闭上电自动运行.Size = new System.Drawing.Size(250, 28);
            this.GB4_3_button_关闭上电自动运行.TabIndex = 1;
            this.GB4_3_button_关闭上电自动运行.Tag = "11";
            this.GB4_3_button_关闭上电自动运行.Text = "关闭上电自动运行";
            this.GB4_3_button_关闭上电自动运行.UseVisualStyleBackColor = true;
            // 
            // GB4_3_button_开启上电自动运行
            // 
            this.GB4_3_button_开启上电自动运行.Location = new System.Drawing.Point(15, 158);
            this.GB4_3_button_开启上电自动运行.Name = "GB4_3_button_开启上电自动运行";
            this.GB4_3_button_开启上电自动运行.Size = new System.Drawing.Size(250, 28);
            this.GB4_3_button_开启上电自动运行.TabIndex = 2;
            this.GB4_3_button_开启上电自动运行.Tag = "10";
            this.GB4_3_button_开启上电自动运行.Text = "开启上电自动运行";
            this.GB4_3_button_开启上电自动运行.UseVisualStyleBackColor = true;
            // 
            // GB4_3_button_停止
            // 
            this.GB4_3_button_停止.Location = new System.Drawing.Point(152, 119);
            this.GB4_3_button_停止.Name = "GB4_3_button_停止";
            this.GB4_3_button_停止.Size = new System.Drawing.Size(112, 25);
            this.GB4_3_button_停止.TabIndex = 3;
            this.GB4_3_button_停止.Tag = "9";
            this.GB4_3_button_停止.Text = "停止";
            this.GB4_3_button_停止.UseVisualStyleBackColor = true;
            this.GB4_3_button_停止.Click += new System.EventHandler(this.GB4_3_button_停止_Click);
            // 
            // GB4_3_button_开始
            // 
            this.GB4_3_button_开始.Location = new System.Drawing.Point(15, 119);
            this.GB4_3_button_开始.Name = "GB4_3_button_开始";
            this.GB4_3_button_开始.Size = new System.Drawing.Size(112, 25);
            this.GB4_3_button_开始.TabIndex = 4;
            this.GB4_3_button_开始.Tag = "8";
            this.GB4_3_button_开始.Text = "开始";
            this.GB4_3_button_开始.UseVisualStyleBackColor = true;
            this.GB4_3_button_开始.Click += new System.EventHandler(this.GB4_3_button_开始_Click);
            // 
            // GB4_3_comboBox_速度档位
            // 
            this.GB4_3_comboBox_速度档位.FormattingEnabled = true;
            this.GB4_3_comboBox_速度档位.Items.AddRange(new object[] {
            "100",
            "50",
            "20",
            "10",
            "5",
            "1"});
            this.GB4_3_comboBox_速度档位.Location = new System.Drawing.Point(132, 70);
            this.GB4_3_comboBox_速度档位.Name = "GB4_3_comboBox_速度档位";
            this.GB4_3_comboBox_速度档位.Size = new System.Drawing.Size(109, 20);
            this.GB4_3_comboBox_速度档位.TabIndex = 5;
            // 
            // GB4_3_label_提示
            // 
            this.GB4_3_label_提示.AutoSize = true;
            this.GB4_3_label_提示.Font = new System.Drawing.Font("宋体", 9F);
            this.GB4_3_label_提示.Location = new System.Drawing.Point(39, 100);
            this.GB4_3_label_提示.Name = "GB4_3_label_提示";
            this.GB4_3_label_提示.Size = new System.Drawing.Size(149, 12);
            this.GB4_3_label_提示.TabIndex = 6;
            this.GB4_3_label_提示.Text = "提示：速度档位范围0-3000";
            // 
            // GB4_3_label_速度档位
            // 
            this.GB4_3_label_速度档位.AutoSize = true;
            this.GB4_3_label_速度档位.Location = new System.Drawing.Point(38, 72);
            this.GB4_3_label_速度档位.Name = "GB4_3_label_速度档位";
            this.GB4_3_label_速度档位.Size = new System.Drawing.Size(53, 12);
            this.GB4_3_label_速度档位.TabIndex = 7;
            this.GB4_3_label_速度档位.Text = "速度档位";
            // 
            // GB4_groupBox4_电机位置控制模式
            // 
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_panel_正转or反转);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_button_停止);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_button_开始);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_label_提示);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_textBox_脉冲数);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_comboBox_速度档位);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_comboBox_模式切换);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_label_脉冲数);
            this.GB4_groupBox4_电机位置控制模式.Controls.Add(this.GB4_4_label_速度档位);
            this.GB4_groupBox4_电机位置控制模式.Location = new System.Drawing.Point(334, 253);
            this.GB4_groupBox4_电机位置控制模式.Name = "GB4_groupBox4_电机位置控制模式";
            this.GB4_groupBox4_电机位置控制模式.Size = new System.Drawing.Size(278, 229);
            this.GB4_groupBox4_电机位置控制模式.TabIndex = 15;
            this.GB4_groupBox4_电机位置控制模式.TabStop = false;
            this.GB4_groupBox4_电机位置控制模式.Text = "电机位置控制模式";
            // 
            // GB4_4_panel_正转or反转
            // 
            this.GB4_4_panel_正转or反转.Controls.Add(this.GB4_4_radioButton_反转);
            this.GB4_4_panel_正转or反转.Controls.Add(this.GB4_4_radioButton_正转);
            this.GB4_4_panel_正转or反转.Location = new System.Drawing.Point(38, 28);
            this.GB4_4_panel_正转or反转.Name = "GB4_4_panel_正转or反转";
            this.GB4_4_panel_正转or反转.Size = new System.Drawing.Size(225, 34);
            this.GB4_4_panel_正转or反转.TabIndex = 0;
            // 
            // GB4_4_radioButton_反转
            // 
            this.GB4_4_radioButton_反转.AutoSize = true;
            this.GB4_4_radioButton_反转.Location = new System.Drawing.Point(131, 9);
            this.GB4_4_radioButton_反转.Name = "GB4_4_radioButton_反转";
            this.GB4_4_radioButton_反转.Size = new System.Drawing.Size(47, 16);
            this.GB4_4_radioButton_反转.TabIndex = 0;
            this.GB4_4_radioButton_反转.TabStop = true;
            this.GB4_4_radioButton_反转.Tag = "";
            this.GB4_4_radioButton_反转.Text = "反转";
            this.GB4_4_radioButton_反转.UseVisualStyleBackColor = true;
            // 
            // GB4_4_radioButton_正转
            // 
            this.GB4_4_radioButton_正转.AutoSize = true;
            this.GB4_4_radioButton_正转.Location = new System.Drawing.Point(13, 9);
            this.GB4_4_radioButton_正转.Name = "GB4_4_radioButton_正转";
            this.GB4_4_radioButton_正转.Size = new System.Drawing.Size(47, 16);
            this.GB4_4_radioButton_正转.TabIndex = 1;
            this.GB4_4_radioButton_正转.TabStop = true;
            this.GB4_4_radioButton_正转.Tag = "";
            this.GB4_4_radioButton_正转.Text = "正转";
            this.GB4_4_radioButton_正转.UseVisualStyleBackColor = true;
            // 
            // GB4_4_button_停止
            // 
            this.GB4_4_button_停止.Location = new System.Drawing.Point(151, 192);
            this.GB4_4_button_停止.Name = "GB4_4_button_停止";
            this.GB4_4_button_停止.Size = new System.Drawing.Size(112, 25);
            this.GB4_4_button_停止.TabIndex = 1;
            this.GB4_4_button_停止.Tag = "38";
            this.GB4_4_button_停止.Text = "停止";
            this.GB4_4_button_停止.UseVisualStyleBackColor = true;
            this.GB4_4_button_停止.Click += new System.EventHandler(this.GB4_4_button_停止_Click);
            // 
            // GB4_4_button_开始
            // 
            this.GB4_4_button_开始.Location = new System.Drawing.Point(14, 192);
            this.GB4_4_button_开始.Name = "GB4_4_button_开始";
            this.GB4_4_button_开始.Size = new System.Drawing.Size(112, 25);
            this.GB4_4_button_开始.TabIndex = 2;
            this.GB4_4_button_开始.Tag = "13";
            this.GB4_4_button_开始.Text = "开始";
            this.GB4_4_button_开始.UseVisualStyleBackColor = true;
            this.GB4_4_button_开始.Click += new System.EventHandler(this.GB4_4_button_开始_Click);
            // 
            // GB4_4_label_提示
            // 
            this.GB4_4_label_提示.Font = new System.Drawing.Font("宋体", 9F);
            this.GB4_4_label_提示.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.GB4_4_label_提示.Location = new System.Drawing.Point(16, 149);
            this.GB4_4_label_提示.Name = "GB4_4_label_提示";
            this.GB4_4_label_提示.Size = new System.Drawing.Size(240, 40);
            this.GB4_4_label_提示.TabIndex = 3;
            this.GB4_4_label_提示.Text = "提示1：在16细分时，3200脉冲 = 360°。\n提示2：坐标取值范围为 -2147483647到2147483647 或 0x00到0xFFFFFFFF。";
            // 
            // GB4_4_textBox_脉冲数
            // 
            this.GB4_4_textBox_脉冲数.Location = new System.Drawing.Point(135, 115);
            this.GB4_4_textBox_脉冲数.MaxLength = 65535;
            this.GB4_4_textBox_脉冲数.Name = "GB4_4_textBox_脉冲数";
            this.GB4_4_textBox_脉冲数.Size = new System.Drawing.Size(106, 21);
            this.GB4_4_textBox_脉冲数.TabIndex = 4;
            // 
            // GB4_4_comboBox_速度档位
            // 
            this.GB4_4_comboBox_速度档位.FormattingEnabled = true;
            this.GB4_4_comboBox_速度档位.Items.AddRange(new object[] {
            "100",
            "50",
            "20",
            "10",
            "5",
            "1"});
            this.GB4_4_comboBox_速度档位.Location = new System.Drawing.Point(135, 79);
            this.GB4_4_comboBox_速度档位.Name = "GB4_4_comboBox_速度档位";
            this.GB4_4_comboBox_速度档位.Size = new System.Drawing.Size(106, 20);
            this.GB4_4_comboBox_速度档位.TabIndex = 5;
            // 
            // GB4_4_comboBox_模式切换
            // 
            this.GB4_4_comboBox_模式切换.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.GB4_4_comboBox_模式切换.FormattingEnabled = true;
            this.GB4_4_comboBox_模式切换.Items.AddRange(new object[] {
            "相对脉冲",
            "绝对脉冲",
            "相对编码",
            "绝对编码"});
            this.GB4_4_comboBox_模式切换.Location = new System.Drawing.Point(40, 116);
            this.GB4_4_comboBox_模式切换.Name = "GB4_4_comboBox_模式切换";
            this.GB4_4_comboBox_模式切换.Size = new System.Drawing.Size(87, 20);
            this.GB4_4_comboBox_模式切换.TabIndex = 6;
            // 
            // GB4_4_label_脉冲数
            // 
            this.GB4_4_label_脉冲数.AutoSize = true;
            this.GB4_4_label_脉冲数.Location = new System.Drawing.Point(40, 118);
            this.GB4_4_label_脉冲数.Name = "GB4_4_label_脉冲数";
            this.GB4_4_label_脉冲数.Size = new System.Drawing.Size(41, 12);
            this.GB4_4_label_脉冲数.TabIndex = 7;
            this.GB4_4_label_脉冲数.Text = "脉冲数";
            // 
            // GB4_4_label_速度档位
            // 
            this.GB4_4_label_速度档位.AutoSize = true;
            this.GB4_4_label_速度档位.Location = new System.Drawing.Point(40, 82);
            this.GB4_4_label_速度档位.Name = "GB4_4_label_速度档位";
            this.GB4_4_label_速度档位.Size = new System.Drawing.Size(53, 12);
            this.GB4_4_label_速度档位.TabIndex = 8;
            this.GB4_4_label_速度档位.Text = "速度档位";
            // 
            // btnReadversion
            // 
            this.btnReadversion.Location = new System.Drawing.Point(12, 459);
            this.btnReadversion.Name = "btnReadversion";
            this.btnReadversion.Size = new System.Drawing.Size(71, 23);
            this.btnReadversion.TabIndex = 16;
            this.btnReadversion.Text = "读取版本";
            this.btnReadversion.UseVisualStyleBackColor = true;
            this.btnReadversion.Click += new System.EventHandler(this.btnReadversion_Click);
            // 
            // btnReadSetting
            // 
            this.btnReadSetting.Location = new System.Drawing.Point(89, 459);
            this.btnReadSetting.Name = "btnReadSetting";
            this.btnReadSetting.Size = new System.Drawing.Size(63, 23);
            this.btnReadSetting.TabIndex = 16;
            this.btnReadSetting.Text = "读取设置";
            this.btnReadSetting.UseVisualStyleBackColor = true;
            this.btnReadSetting.Click += new System.EventHandler(this.btnReadSubdiv_Click);
            // 
            // btnReadStatus
            // 
            this.btnReadStatus.Location = new System.Drawing.Point(158, 459);
            this.btnReadStatus.Name = "btnReadStatus";
            this.btnReadStatus.Size = new System.Drawing.Size(75, 23);
            this.btnReadStatus.TabIndex = 16;
            this.btnReadStatus.Text = "全部状态";
            this.btnReadStatus.UseVisualStyleBackColor = true;
            this.btnReadStatus.Click += new System.EventHandler(this.btnReadStatus_Click);
            // 
            // btnRunstate
            // 
            this.btnRunstate.Location = new System.Drawing.Point(238, 459);
            this.btnRunstate.Name = "btnRunstate";
            this.btnRunstate.Size = new System.Drawing.Size(75, 23);
            this.btnRunstate.TabIndex = 16;
            this.btnRunstate.Text = "运行状态";
            this.btnRunstate.UseVisualStyleBackColor = true;
            this.btnRunstate.Click += new System.EventHandler(this.btnRunstate_Click);
            // 
            // RS485调试
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 12F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(669, 493);
            this.Controls.Add(this.btnRunstate);
            this.Controls.Add(this.btnReadStatus);
            this.Controls.Add(this.btnReadSetting);
            this.Controls.Add(this.btnReadversion);
            this.Controls.Add(this.GB4_groupBox4_电机位置控制模式);
            this.Controls.Add(this.GB4_groupBox3_电机速度控制模式);
            this.Controls.Add(this.F1_groupBox6_数据日志);
            this.Controls.Add(this.F1_groupBox1_连接设置);
            this.Name = "RS485调试";
            this.Text = "RS485调试";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.RS485调试_FormClosing);
            this.Load += new System.EventHandler(this.Form1_Load);
            this.F1_groupBox1_连接设置.ResumeLayout(false);
            this.F1_groupBox1_连接设置.PerformLayout();
            this.F1_groupBox6_数据日志.ResumeLayout(false);
            this.F1_groupBox6_数据日志.PerformLayout();
            this.GB4_groupBox3_电机速度控制模式.ResumeLayout(false);
            this.GB4_groupBox3_电机速度控制模式.PerformLayout();
            this.GB4_3_panel_正转or反转.ResumeLayout(false);
            this.GB4_3_panel_正转or反转.PerformLayout();
            this.GB4_groupBox4_电机位置控制模式.ResumeLayout(false);
            this.GB4_groupBox4_电机位置控制模式.PerformLayout();
            this.GB4_4_panel_正转or反转.ResumeLayout(false);
            this.GB4_4_panel_正转or反转.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.GroupBox F1_groupBox1_连接设置;
        private System.Windows.Forms.ComboBox GB1_comboBox_通讯地址;
        private System.Windows.Forms.Label GB1_label_通讯地址;
        private System.Windows.Forms.GroupBox F1_groupBox6_数据日志;
        private System.Windows.Forms.TextBox GB6_textBox_数据日志;
        private System.Windows.Forms.GroupBox GB4_groupBox3_电机速度控制模式;
        private System.Windows.Forms.Panel GB4_3_panel_正转or反转;
        private System.Windows.Forms.RadioButton GB4_3_radioButton_反转;
        private System.Windows.Forms.RadioButton GB4_3_radioButton_正转;
        private System.Windows.Forms.Button GB4_3_button_关闭上电自动运行;
        private System.Windows.Forms.Button GB4_3_button_开启上电自动运行;
        private System.Windows.Forms.Button GB4_3_button_停止;
        private System.Windows.Forms.Button GB4_3_button_开始;
        private System.Windows.Forms.ComboBox GB4_3_comboBox_速度档位;
        private System.Windows.Forms.Label GB4_3_label_提示;
        private System.Windows.Forms.Label GB4_3_label_速度档位;
        private System.Windows.Forms.GroupBox GB4_groupBox4_电机位置控制模式;
        private System.Windows.Forms.Panel GB4_4_panel_正转or反转;
        private System.Windows.Forms.RadioButton GB4_4_radioButton_反转;
        private System.Windows.Forms.RadioButton GB4_4_radioButton_正转;
        private System.Windows.Forms.Button GB4_4_button_停止;
        private System.Windows.Forms.Button GB4_4_button_开始;
        private System.Windows.Forms.Label GB4_4_label_提示;
        private System.Windows.Forms.TextBox GB4_4_textBox_脉冲数;
        private System.Windows.Forms.ComboBox GB4_4_comboBox_速度档位;
        private System.Windows.Forms.ComboBox GB4_4_comboBox_模式切换;
        private System.Windows.Forms.Label GB4_4_label_脉冲数;
        private System.Windows.Forms.Label GB4_4_label_速度档位;
        private System.IO.Ports.SerialPort serialPort1;
        private System.Windows.Forms.Button btnReadversion;
        private System.Windows.Forms.Button btnReadSetting;
        private System.Windows.Forms.Button btnReadStatus;
        private System.Windows.Forms.Button btnRunstate;
    }
}

