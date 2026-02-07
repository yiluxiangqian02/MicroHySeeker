namespace COMtest
{
    partial class Manualwindow
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Manualwindow));
            this.cmbChannelList = new System.Windows.Forms.ComboBox();
            this.fwdrunBtn = new System.Windows.Forms.Button();
            this.stopBtn = new System.Windows.Forms.Button();
            this.speedBox = new System.Windows.Forms.NumericUpDown();
            this.spdunitCmb = new System.Windows.Forms.ComboBox();
            this.ffBtn = new System.Windows.Forms.Button();
            this.frevBtn = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.testMsgbox = new System.Windows.Forms.TextBox();
            this.label3 = new System.Windows.Forms.Label();
            this.label4 = new System.Windows.Forms.Label();
            this.lblPort = new System.Windows.Forms.Label();
            ((System.ComponentModel.ISupportInitialize)(this.speedBox)).BeginInit();
            this.SuspendLayout();
            // 
            // cmbChannelList
            // 
            this.cmbChannelList.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbChannelList.FormattingEnabled = true;
            resources.ApplyResources(this.cmbChannelList, "cmbChannelList");
            this.cmbChannelList.Name = "cmbChannelList";
            this.cmbChannelList.SelectedIndexChanged += new System.EventHandler(this.portsList_SelectedIndexChanged);
            // 
            // fwdrunBtn
            // 
            resources.ApplyResources(this.fwdrunBtn, "fwdrunBtn");
            this.fwdrunBtn.Name = "fwdrunBtn";
            this.fwdrunBtn.UseVisualStyleBackColor = true;
            this.fwdrunBtn.Click += new System.EventHandler(this.runBtn_Click);
            // 
            // stopBtn
            // 
            resources.ApplyResources(this.stopBtn, "stopBtn");
            this.stopBtn.ForeColor = System.Drawing.Color.Maroon;
            this.stopBtn.Name = "stopBtn";
            this.stopBtn.UseVisualStyleBackColor = true;
            this.stopBtn.Click += new System.EventHandler(this.stopBtn_Click);
            // 
            // speedBox
            // 
            resources.ApplyResources(this.speedBox, "speedBox");
            this.speedBox.Maximum = new decimal(new int[] {
            99,
            0,
            0,
            0});
            this.speedBox.Minimum = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.speedBox.Name = "speedBox";
            this.speedBox.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            // 
            // spdunitCmb
            // 
            this.spdunitCmb.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.spdunitCmb.FormattingEnabled = true;
            this.spdunitCmb.Items.AddRange(new object[] {
            resources.GetString("spdunitCmb.Items"),
            resources.GetString("spdunitCmb.Items1"),
            resources.GetString("spdunitCmb.Items2")});
            resources.ApplyResources(this.spdunitCmb, "spdunitCmb");
            this.spdunitCmb.Name = "spdunitCmb";
            // 
            // ffBtn
            // 
            resources.ApplyResources(this.ffBtn, "ffBtn");
            this.ffBtn.Name = "ffBtn";
            this.ffBtn.UseVisualStyleBackColor = true;
            this.ffBtn.MouseDown += new System.Windows.Forms.MouseEventHandler(this.ffBtn_MouseDown);
            this.ffBtn.MouseUp += new System.Windows.Forms.MouseEventHandler(this.ffBtn_MouseUp);
            // 
            // frevBtn
            // 
            resources.ApplyResources(this.frevBtn, "frevBtn");
            this.frevBtn.Name = "frevBtn";
            this.frevBtn.UseVisualStyleBackColor = true;
            this.frevBtn.MouseDown += new System.Windows.Forms.MouseEventHandler(this.frevBtn_MouseDown);
            this.frevBtn.MouseUp += new System.Windows.Forms.MouseEventHandler(this.frevBtn_MouseUp);
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // label2
            // 
            resources.ApplyResources(this.label2, "label2");
            this.label2.Name = "label2";
            // 
            // testMsgbox
            // 
            resources.ApplyResources(this.testMsgbox, "testMsgbox");
            this.testMsgbox.Name = "testMsgbox";
            this.testMsgbox.ReadOnly = true;
            // 
            // label3
            // 
            resources.ApplyResources(this.label3, "label3");
            this.label3.Name = "label3";
            // 
            // label4
            // 
            resources.ApplyResources(this.label4, "label4");
            this.label4.Name = "label4";
            // 
            // lblPort
            // 
            resources.ApplyResources(this.lblPort, "lblPort");
            this.lblPort.Name = "lblPort";
            // 
            // Manualwindow
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.label3);
            this.Controls.Add(this.testMsgbox);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.lblPort);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.frevBtn);
            this.Controls.Add(this.ffBtn);
            this.Controls.Add(this.spdunitCmb);
            this.Controls.Add(this.speedBox);
            this.Controls.Add(this.stopBtn);
            this.Controls.Add(this.fwdrunBtn);
            this.Controls.Add(this.cmbChannelList);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
            this.Name = "Manualwindow";
            this.Load += new System.EventHandler(this.Form_Load);
            ((System.ComponentModel.ISupportInitialize)(this.speedBox)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion
        private System.Windows.Forms.ComboBox cmbChannelList;
        private System.Windows.Forms.Button fwdrunBtn;
        private System.Windows.Forms.Button stopBtn;
        private System.Windows.Forms.NumericUpDown speedBox;
        private System.Windows.Forms.ComboBox spdunitCmb;
        private System.Windows.Forms.Button ffBtn;
        private System.Windows.Forms.Button frevBtn;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.TextBox testMsgbox;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.Label lblPort;
    }
}

