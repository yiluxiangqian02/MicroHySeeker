namespace eChemSDL
{
    partial class JumptoCmbExp
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(JumptoCmbExp));
            this.btnJumptoCmbExp = new System.Windows.Forms.Button();
            this.numCmbIndex = new System.Windows.Forms.NumericUpDown();
            this.btnRunSelected = new System.Windows.Forms.Button();
            ((System.ComponentModel.ISupportInitialize)(this.numCmbIndex)).BeginInit();
            this.SuspendLayout();
            // 
            // btnJumptoCmbExp
            // 
            resources.ApplyResources(this.btnJumptoCmbExp, "btnJumptoCmbExp");
            this.btnJumptoCmbExp.DialogResult = System.Windows.Forms.DialogResult.OK;
            this.btnJumptoCmbExp.Name = "btnJumptoCmbExp";
            this.btnJumptoCmbExp.UseVisualStyleBackColor = true;
            this.btnJumptoCmbExp.Click += new System.EventHandler(this.btnJumptoCmbExp_Click);
            // 
            // numCmbIndex
            // 
            resources.ApplyResources(this.numCmbIndex, "numCmbIndex");
            this.numCmbIndex.Maximum = new decimal(new int[] {
            100000,
            0,
            0,
            0});
            this.numCmbIndex.Minimum = new decimal(new int[] {
            1,
            0,
            0,
            0});
            this.numCmbIndex.Name = "numCmbIndex";
            this.numCmbIndex.Value = new decimal(new int[] {
            1,
            0,
            0,
            0});
            // 
            // btnRunSelected
            // 
            resources.ApplyResources(this.btnRunSelected, "btnRunSelected");
            this.btnRunSelected.Name = "btnRunSelected";
            this.btnRunSelected.UseVisualStyleBackColor = true;
            this.btnRunSelected.Click += new System.EventHandler(this.btnRunSelected_Click);
            // 
            // JumptoCmbExp
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.numCmbIndex);
            this.Controls.Add(this.btnJumptoCmbExp);
            this.Controls.Add(this.btnRunSelected);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedToolWindow;
            this.Name = "JumptoCmbExp";
            this.ShowIcon = false;
            this.ShowInTaskbar = false;
            this.Load += new System.EventHandler(this.JumptoCmbExp_Load);
            ((System.ComponentModel.ISupportInitialize)(this.numCmbIndex)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button btnJumptoCmbExp;
        private System.Windows.Forms.NumericUpDown numCmbIndex;
        private System.Windows.Forms.Button btnRunSelected;
    }
}