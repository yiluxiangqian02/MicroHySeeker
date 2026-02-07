namespace eChemSDL
{
    partial class Tester
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Tester));
            this.usersettings = new System.Windows.Forms.ListBox();
            this.label1 = new System.Windows.Forms.Label();
            this.Clear = new System.Windows.Forms.Button();
            this.label2 = new System.Windows.Forms.Label();
            this.testMsg = new System.Windows.Forms.TextBox();
            this.btnFloat = new System.Windows.Forms.Button();
            this.cmbType = new System.Windows.Forms.ComboBox();
            this.txtFloat = new System.Windows.Forms.TextBox();
            this.SuspendLayout();
            // 
            // usersettings
            // 
            resources.ApplyResources(this.usersettings, "usersettings");
            this.usersettings.FormattingEnabled = true;
            this.usersettings.Name = "usersettings";
            this.usersettings.SelectionMode = System.Windows.Forms.SelectionMode.MultiExtended;
            this.usersettings.SelectedIndexChanged += new System.EventHandler(this.usersettings_SelectedIndexChanged);
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // Clear
            // 
            resources.ApplyResources(this.Clear, "Clear");
            this.Clear.Name = "Clear";
            this.Clear.UseVisualStyleBackColor = true;
            this.Clear.Click += new System.EventHandler(this.Clear_Click);
            // 
            // label2
            // 
            resources.ApplyResources(this.label2, "label2");
            this.label2.Name = "label2";
            // 
            // testMsg
            // 
            resources.ApplyResources(this.testMsg, "testMsg");
            this.testMsg.Name = "testMsg";
            // 
            // btnFloat
            // 
            resources.ApplyResources(this.btnFloat, "btnFloat");
            this.btnFloat.Name = "btnFloat";
            this.btnFloat.UseVisualStyleBackColor = true;
            this.btnFloat.Click += new System.EventHandler(this.btnFloat_Click);
            // 
            // cmbType
            // 
            this.cmbType.FormattingEnabled = true;
            this.cmbType.Items.AddRange(new object[] {
            resources.GetString("cmbType.Items"),
            resources.GetString("cmbType.Items1"),
            resources.GetString("cmbType.Items2")});
            resources.ApplyResources(this.cmbType, "cmbType");
            this.cmbType.Name = "cmbType";
            // 
            // txtFloat
            // 
            resources.ApplyResources(this.txtFloat, "txtFloat");
            this.txtFloat.Name = "txtFloat";
            this.txtFloat.TextChanged += new System.EventHandler(this.txtFloat_TextChanged);
            // 
            // Tester
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.txtFloat);
            this.Controls.Add(this.cmbType);
            this.Controls.Add(this.btnFloat);
            this.Controls.Add(this.testMsg);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.Clear);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.usersettings);
            this.Name = "Tester";
            this.Load += new System.EventHandler(this.Test_Load);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.ListBox usersettings;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Button Clear;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.TextBox testMsg;
        private System.Windows.Forms.Button btnFloat;
        private System.Windows.Forms.ComboBox cmbType;
        private System.Windows.Forms.TextBox txtFloat;
    }
}