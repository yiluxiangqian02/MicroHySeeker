namespace eChemSDL
{
    partial class ManMotorsOnRS485
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(ManMotorsOnRS485));
            this.label3 = new System.Windows.Forms.Label();
            this.testMsgbox = new System.Windows.Forms.TextBox();
            this.label2 = new System.Windows.Forms.Label();
            this.speedBox = new System.Windows.Forms.NumericUpDown();
            this.label4 = new System.Windows.Forms.Label();
            this.addressbox = new System.Windows.Forms.NumericUpDown();
            this.btnSetAddr = new System.Windows.Forms.Button();
            this.buttonGetSettings = new System.Windows.Forms.Button();
            this.buttonCWCont = new System.Windows.Forms.Button();
            this.buttonCCWRunCont = new System.Windows.Forms.Button();
            this.buttonStop = new System.Windows.Forms.Button();
            this.label5 = new System.Windows.Forms.Label();
            this.textBoxCommand = new System.Windows.Forms.TextBox();
            this.buttonSend = new System.Windows.Forms.Button();
            this.btnCheckCmd = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.lblCom = new System.Windows.Forms.Label();
            ((System.ComponentModel.ISupportInitialize)(this.speedBox)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.addressbox)).BeginInit();
            this.SuspendLayout();
            // 
            // label3
            // 
            resources.ApplyResources(this.label3, "label3");
            this.label3.Name = "label3";
            // 
            // testMsgbox
            // 
            resources.ApplyResources(this.testMsgbox, "testMsgbox");
            this.testMsgbox.Name = "testMsgbox";
            this.testMsgbox.ReadOnly = true;
            // 
            // label2
            // 
            resources.ApplyResources(this.label2, "label2");
            this.label2.Name = "label2";
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
            30,
            0,
            0,
            0});
            // 
            // label4
            // 
            resources.ApplyResources(this.label4, "label4");
            this.label4.Name = "label4";
            // 
            // addressbox
            // 
            resources.ApplyResources(this.addressbox, "addressbox");
            this.addressbox.Maximum = new decimal(new int[] {
            99,
            0,
            0,
            0});
            this.addressbox.Name = "addressbox";
            this.addressbox.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            // 
            // btnSetAddr
            // 
            resources.ApplyResources(this.btnSetAddr, "btnSetAddr");
            this.btnSetAddr.Name = "btnSetAddr";
            this.btnSetAddr.UseVisualStyleBackColor = true;
            this.btnSetAddr.Click += new System.EventHandler(this.btnSetAddr_Click);
            // 
            // buttonGetSettings
            // 
            resources.ApplyResources(this.buttonGetSettings, "buttonGetSettings");
            this.buttonGetSettings.Name = "buttonGetSettings";
            this.buttonGetSettings.UseVisualStyleBackColor = true;
            // 
            // buttonCWCont
            // 
            resources.ApplyResources(this.buttonCWCont, "buttonCWCont");
            this.buttonCWCont.Name = "buttonCWCont";
            this.buttonCWCont.UseVisualStyleBackColor = true;
            this.buttonCWCont.Click += new System.EventHandler(this.buttonCWCont_Click);
            // 
            // buttonCCWRunCont
            // 
            resources.ApplyResources(this.buttonCCWRunCont, "buttonCCWRunCont");
            this.buttonCCWRunCont.Name = "buttonCCWRunCont";
            this.buttonCCWRunCont.UseVisualStyleBackColor = true;
            this.buttonCCWRunCont.Click += new System.EventHandler(this.buttonCCWRunCont_Click);
            // 
            // buttonStop
            // 
            resources.ApplyResources(this.buttonStop, "buttonStop");
            this.buttonStop.Name = "buttonStop";
            this.buttonStop.UseVisualStyleBackColor = true;
            this.buttonStop.Click += new System.EventHandler(this.buttonStop_Click);
            // 
            // label5
            // 
            resources.ApplyResources(this.label5, "label5");
            this.label5.Name = "label5";
            // 
            // textBoxCommand
            // 
            resources.ApplyResources(this.textBoxCommand, "textBoxCommand");
            this.textBoxCommand.Name = "textBoxCommand";
            // 
            // buttonSend
            // 
            resources.ApplyResources(this.buttonSend, "buttonSend");
            this.buttonSend.Name = "buttonSend";
            this.buttonSend.UseVisualStyleBackColor = true;
            this.buttonSend.Click += new System.EventHandler(this.buttonSend_Click);
            // 
            // btnCheckCmd
            // 
            resources.ApplyResources(this.btnCheckCmd, "btnCheckCmd");
            this.btnCheckCmd.Name = "btnCheckCmd";
            this.btnCheckCmd.UseVisualStyleBackColor = true;
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // lblCom
            // 
            resources.ApplyResources(this.lblCom, "lblCom");
            this.lblCom.Name = "lblCom";
            // 
            // ManMotorsOnRS485
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.btnCheckCmd);
            this.Controls.Add(this.buttonSend);
            this.Controls.Add(this.textBoxCommand);
            this.Controls.Add(this.buttonStop);
            this.Controls.Add(this.buttonGetSettings);
            this.Controls.Add(this.btnSetAddr);
            this.Controls.Add(this.label5);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.testMsgbox);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.lblCom);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.buttonCWCont);
            this.Controls.Add(this.buttonCCWRunCont);
            this.Controls.Add(this.addressbox);
            this.Controls.Add(this.speedBox);
            this.Name = "ManMotorsOnRS485";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.MotorsOnRS485Panel_FormClosing);
            this.Load += new System.EventHandler(this.ManMotorsOnRS485_Load);
            ((System.ComponentModel.ISupportInitialize)(this.speedBox)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.addressbox)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.TextBox testMsgbox;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.NumericUpDown speedBox;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.NumericUpDown addressbox;
        private System.Windows.Forms.Button btnSetAddr;
        private System.Windows.Forms.Button buttonGetSettings;
        private System.Windows.Forms.Button buttonCWCont;
        private System.Windows.Forms.Button buttonCCWRunCont;
        private System.Windows.Forms.Button buttonStop;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.TextBox textBoxCommand;
        private System.Windows.Forms.Button buttonSend;
        private System.Windows.Forms.Button btnCheckCmd;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label lblCom;
    }
}