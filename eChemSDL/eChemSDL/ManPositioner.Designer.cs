namespace eChemSDL
{
    partial class ManPositioner
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(ManPositioner));
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle1 = new System.Windows.Forms.DataGridViewCellStyle();
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle2 = new System.Windows.Forms.DataGridViewCellStyle();
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle3 = new System.Windows.Forms.DataGridViewCellStyle();
            System.Windows.Forms.DataGridViewCellStyle dataGridViewCellStyle4 = new System.Windows.Forms.DataGridViewCellStyle();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.lblSpeed = new System.Windows.Forms.Label();
            this.lblPort = new System.Windows.Forms.Label();
            this.dataGridView1 = new System.Windows.Forms.DataGridView();
            this.ColAxis = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.ColCount = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.ColDist = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.ColPulse = new System.Windows.Forms.DataGridViewTextBoxColumn();
            this.label1 = new System.Windows.Forms.Label();
            this.label3 = new System.Windows.Forms.Label();
            this.groupBox2 = new System.Windows.Forms.GroupBox();
            this.btnPickNext = new System.Windows.Forms.Button();
            this.btnNext = new System.Windows.Forms.Button();
            this.btnZero = new System.Windows.Forms.Button();
            this.btnReset = new System.Windows.Forms.Button();
            this.btnMove = new System.Windows.Forms.Button();
            this.txtLay = new System.Windows.Forms.TextBox();
            this.label15 = new System.Windows.Forms.Label();
            this.txtCol = new System.Windows.Forms.TextBox();
            this.label14 = new System.Windows.Forms.Label();
            this.txtRow = new System.Windows.Forms.TextBox();
            this.label13 = new System.Windows.Forms.Label();
            this.groupBox3 = new System.Windows.Forms.GroupBox();
            this.btnSendCmd = new System.Windows.Forms.Button();
            this.txtCmd = new System.Windows.Forms.TextBox();
            this.txtMsg = new System.Windows.Forms.TextBox();
            this.groupBox1.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView1)).BeginInit();
            this.groupBox2.SuspendLayout();
            this.groupBox3.SuspendLayout();
            this.SuspendLayout();
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.lblSpeed);
            this.groupBox1.Controls.Add(this.lblPort);
            this.groupBox1.Controls.Add(this.dataGridView1);
            this.groupBox1.Controls.Add(this.label1);
            this.groupBox1.Controls.Add(this.label3);
            resources.ApplyResources(this.groupBox1, "groupBox1");
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.TabStop = false;
            // 
            // lblSpeed
            // 
            resources.ApplyResources(this.lblSpeed, "lblSpeed");
            this.lblSpeed.Name = "lblSpeed";
            // 
            // lblPort
            // 
            resources.ApplyResources(this.lblPort, "lblPort");
            this.lblPort.Name = "lblPort";
            // 
            // dataGridView1
            // 
            this.dataGridView1.AllowUserToAddRows = false;
            this.dataGridView1.AllowUserToDeleteRows = false;
            this.dataGridView1.AllowUserToResizeColumns = false;
            this.dataGridView1.AllowUserToResizeRows = false;
            this.dataGridView1.BackgroundColor = System.Drawing.SystemColors.Control;
            this.dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.dataGridView1.Columns.AddRange(new System.Windows.Forms.DataGridViewColumn[] {
            this.ColAxis,
            this.ColCount,
            this.ColDist,
            this.ColPulse});
            resources.ApplyResources(this.dataGridView1, "dataGridView1");
            this.dataGridView1.Name = "dataGridView1";
            this.dataGridView1.ReadOnly = true;
            this.dataGridView1.RowHeadersVisible = false;
            this.dataGridView1.RowTemplate.Height = 23;
            // 
            // ColAxis
            // 
            this.ColAxis.DataPropertyName = "Name";
            dataGridViewCellStyle1.BackColor = System.Drawing.SystemColors.Control;
            this.ColAxis.DefaultCellStyle = dataGridViewCellStyle1;
            resources.ApplyResources(this.ColAxis, "ColAxis");
            this.ColAxis.Name = "ColAxis";
            this.ColAxis.ReadOnly = true;
            // 
            // ColCount
            // 
            this.ColCount.DataPropertyName = "max";
            dataGridViewCellStyle2.BackColor = System.Drawing.SystemColors.Control;
            this.ColCount.DefaultCellStyle = dataGridViewCellStyle2;
            resources.ApplyResources(this.ColCount, "ColCount");
            this.ColCount.Name = "ColCount";
            this.ColCount.ReadOnly = true;
            // 
            // ColDist
            // 
            this.ColDist.DataPropertyName = "cm";
            dataGridViewCellStyle3.BackColor = System.Drawing.SystemColors.Control;
            this.ColDist.DefaultCellStyle = dataGridViewCellStyle3;
            resources.ApplyResources(this.ColDist, "ColDist");
            this.ColDist.Name = "ColDist";
            this.ColDist.ReadOnly = true;
            // 
            // ColPulse
            // 
            this.ColPulse.DataPropertyName = "pulses";
            dataGridViewCellStyle4.BackColor = System.Drawing.SystemColors.Control;
            this.ColPulse.DefaultCellStyle = dataGridViewCellStyle4;
            resources.ApplyResources(this.ColPulse, "ColPulse");
            this.ColPulse.Name = "ColPulse";
            this.ColPulse.ReadOnly = true;
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // label3
            // 
            resources.ApplyResources(this.label3, "label3");
            this.label3.Name = "label3";
            // 
            // groupBox2
            // 
            this.groupBox2.Controls.Add(this.btnPickNext);
            this.groupBox2.Controls.Add(this.btnNext);
            this.groupBox2.Controls.Add(this.btnZero);
            this.groupBox2.Controls.Add(this.btnReset);
            this.groupBox2.Controls.Add(this.btnMove);
            this.groupBox2.Controls.Add(this.txtLay);
            this.groupBox2.Controls.Add(this.label15);
            this.groupBox2.Controls.Add(this.txtCol);
            this.groupBox2.Controls.Add(this.label14);
            this.groupBox2.Controls.Add(this.txtRow);
            this.groupBox2.Controls.Add(this.label13);
            resources.ApplyResources(this.groupBox2, "groupBox2");
            this.groupBox2.Name = "groupBox2";
            this.groupBox2.TabStop = false;
            // 
            // btnPickNext
            // 
            resources.ApplyResources(this.btnPickNext, "btnPickNext");
            this.btnPickNext.Name = "btnPickNext";
            this.btnPickNext.UseVisualStyleBackColor = true;
            this.btnPickNext.Click += new System.EventHandler(this.btnPickNext_Click);
            // 
            // btnNext
            // 
            resources.ApplyResources(this.btnNext, "btnNext");
            this.btnNext.Name = "btnNext";
            this.btnNext.UseVisualStyleBackColor = true;
            this.btnNext.Click += new System.EventHandler(this.btnNext_Click);
            // 
            // btnZero
            // 
            resources.ApplyResources(this.btnZero, "btnZero");
            this.btnZero.Name = "btnZero";
            this.btnZero.UseVisualStyleBackColor = true;
            this.btnZero.Click += new System.EventHandler(this.btnZero_Click);
            // 
            // btnReset
            // 
            resources.ApplyResources(this.btnReset, "btnReset");
            this.btnReset.Name = "btnReset";
            this.btnReset.UseVisualStyleBackColor = true;
            this.btnReset.Click += new System.EventHandler(this.btnReset_Click);
            // 
            // btnMove
            // 
            resources.ApplyResources(this.btnMove, "btnMove");
            this.btnMove.Name = "btnMove";
            this.btnMove.UseVisualStyleBackColor = true;
            this.btnMove.Click += new System.EventHandler(this.btnMove_Click);
            // 
            // txtLay
            // 
            resources.ApplyResources(this.txtLay, "txtLay");
            this.txtLay.Name = "txtLay";
            // 
            // label15
            // 
            resources.ApplyResources(this.label15, "label15");
            this.label15.Name = "label15";
            // 
            // txtCol
            // 
            resources.ApplyResources(this.txtCol, "txtCol");
            this.txtCol.Name = "txtCol";
            // 
            // label14
            // 
            resources.ApplyResources(this.label14, "label14");
            this.label14.Name = "label14";
            // 
            // txtRow
            // 
            resources.ApplyResources(this.txtRow, "txtRow");
            this.txtRow.Name = "txtRow";
            // 
            // label13
            // 
            resources.ApplyResources(this.label13, "label13");
            this.label13.Name = "label13";
            // 
            // groupBox3
            // 
            resources.ApplyResources(this.groupBox3, "groupBox3");
            this.groupBox3.Controls.Add(this.btnSendCmd);
            this.groupBox3.Controls.Add(this.txtCmd);
            this.groupBox3.Controls.Add(this.txtMsg);
            this.groupBox3.Name = "groupBox3";
            this.groupBox3.TabStop = false;
            // 
            // btnSendCmd
            // 
            resources.ApplyResources(this.btnSendCmd, "btnSendCmd");
            this.btnSendCmd.Name = "btnSendCmd";
            this.btnSendCmd.UseVisualStyleBackColor = true;
            this.btnSendCmd.Click += new System.EventHandler(this.btnSendCmd_Click);
            // 
            // txtCmd
            // 
            resources.ApplyResources(this.txtCmd, "txtCmd");
            this.txtCmd.Name = "txtCmd";
            // 
            // txtMsg
            // 
            resources.ApplyResources(this.txtMsg, "txtMsg");
            this.txtMsg.Name = "txtMsg";
            this.txtMsg.ReadOnly = true;
            // 
            // ManPositioner
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.groupBox3);
            this.Controls.Add(this.groupBox2);
            this.Controls.Add(this.groupBox1);
            this.Name = "ManPositioner";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.ManPositioner_FormClosing);
            this.Load += new System.EventHandler(this.ManPositioner_Load);
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView1)).EndInit();
            this.groupBox2.ResumeLayout(false);
            this.groupBox2.PerformLayout();
            this.groupBox3.ResumeLayout(false);
            this.groupBox3.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.DataGridView dataGridView1;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label lblPort;
        private System.Windows.Forms.GroupBox groupBox2;
        private System.Windows.Forms.TextBox txtLay;
        private System.Windows.Forms.Label label15;
        private System.Windows.Forms.TextBox txtCol;
        private System.Windows.Forms.Label label14;
        private System.Windows.Forms.TextBox txtRow;
        private System.Windows.Forms.Label label13;
        private System.Windows.Forms.Button btnReset;
        private System.Windows.Forms.Button btnMove;
        private System.Windows.Forms.DataGridViewTextBoxColumn ColAxis;
        private System.Windows.Forms.DataGridViewTextBoxColumn ColCount;
        private System.Windows.Forms.DataGridViewTextBoxColumn ColDist;
        private System.Windows.Forms.DataGridViewTextBoxColumn ColPulse;
        private System.Windows.Forms.GroupBox groupBox3;
        private System.Windows.Forms.TextBox txtMsg;
        private System.Windows.Forms.Button btnSendCmd;
        private System.Windows.Forms.TextBox txtCmd;
        private System.Windows.Forms.Button btnZero;
        private System.Windows.Forms.Button btnNext;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Label lblSpeed;
        private System.Windows.Forms.Button btnPickNext;
    }
}