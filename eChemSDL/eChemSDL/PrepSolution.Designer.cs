namespace eChemSDL
{
    partial class PrepSolution
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(PrepSolution));
            this.startMake = new System.Windows.Forms.Button();
            this.cancel = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // startMake
            // 
            resources.ApplyResources(this.startMake, "startMake");
            this.startMake.DialogResult = System.Windows.Forms.DialogResult.OK;
            this.startMake.Name = "startMake";
            this.startMake.UseVisualStyleBackColor = true;
            this.startMake.Click += new System.EventHandler(this.startMake_Click);
            // 
            // cancel
            // 
            resources.ApplyResources(this.cancel, "cancel");
            this.cancel.DialogResult = System.Windows.Forms.DialogResult.Cancel;
            this.cancel.Name = "cancel";
            this.cancel.UseVisualStyleBackColor = true;
            // 
            // PrepSolution
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.cancel);
            this.Controls.Add(this.startMake);
            this.Name = "PrepSolution";
            this.Load += new System.EventHandler(this.MakeSolution_Load);
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button startMake;
        private System.Windows.Forms.Button cancel;
    }
}