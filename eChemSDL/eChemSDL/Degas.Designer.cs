namespace eChemSDL
{
    partial class Degas
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Degas));
            this.btnSelNone = new System.Windows.Forms.Button();
            this.btnDegas = new System.Windows.Forms.Button();
            this.btnSelAll = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // btnSelNone
            // 
            resources.ApplyResources(this.btnSelNone, "btnSelNone");
            this.btnSelNone.Name = "btnSelNone";
            this.btnSelNone.UseVisualStyleBackColor = true;
            this.btnSelNone.Click += new System.EventHandler(this.btnSelNone_Click);
            // 
            // btnDegas
            // 
            resources.ApplyResources(this.btnDegas, "btnDegas");
            this.btnDegas.Name = "btnDegas";
            this.btnDegas.UseVisualStyleBackColor = true;
            this.btnDegas.Click += new System.EventHandler(this.btnDegas_Click);
            // 
            // btnSelAll
            // 
            resources.ApplyResources(this.btnSelAll, "btnSelAll");
            this.btnSelAll.Name = "btnSelAll";
            this.btnSelAll.UseVisualStyleBackColor = true;
            this.btnSelAll.Click += new System.EventHandler(this.btnSelAll_Click);
            // 
            // Degas
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.btnDegas);
            this.Controls.Add(this.btnSelAll);
            this.Controls.Add(this.btnSelNone);
            this.Name = "Degas";
            this.Load += new System.EventHandler(this.Degas_Load);
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button btnSelNone;
        private System.Windows.Forms.Button btnDegas;
        private System.Windows.Forms.Button btnSelAll;
    }
}