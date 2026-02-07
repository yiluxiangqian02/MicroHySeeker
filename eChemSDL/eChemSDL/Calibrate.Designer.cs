namespace eChemSDL
{
    partial class Calibrate
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(Calibrate));
            this.label1 = new System.Windows.Forms.Label();
            this.cmbAddress = new System.Windows.Forms.ComboBox();
            this.label2 = new System.Windows.Forms.Label();
            this.txtVol = new System.Windows.Forms.TextBox();
            this.label3 = new System.Windows.Forms.Label();
            this.btnInject = new System.Windows.Forms.Button();
            this.label4 = new System.Windows.Forms.Label();
            this.txtMass = new System.Windows.Forms.TextBox();
            this.label5 = new System.Windows.Forms.Label();
            this.btnCalib = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // label1
            // 
            resources.ApplyResources(this.label1, "label1");
            this.label1.Name = "label1";
            // 
            // cmbAddress
            // 
            this.cmbAddress.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList;
            this.cmbAddress.FormattingEnabled = true;
            resources.ApplyResources(this.cmbAddress, "cmbAddress");
            this.cmbAddress.Name = "cmbAddress";
            // 
            // label2
            // 
            resources.ApplyResources(this.label2, "label2");
            this.label2.Name = "label2";
            // 
            // txtVol
            // 
            resources.ApplyResources(this.txtVol, "txtVol");
            this.txtVol.Name = "txtVol";
            // 
            // label3
            // 
            resources.ApplyResources(this.label3, "label3");
            this.label3.Name = "label3";
            // 
            // btnInject
            // 
            resources.ApplyResources(this.btnInject, "btnInject");
            this.btnInject.Name = "btnInject";
            this.btnInject.UseVisualStyleBackColor = true;
            this.btnInject.Click += new System.EventHandler(this.injectBtn_Click);
            // 
            // label4
            // 
            resources.ApplyResources(this.label4, "label4");
            this.label4.Name = "label4";
            // 
            // txtMass
            // 
            resources.ApplyResources(this.txtMass, "txtMass");
            this.txtMass.Name = "txtMass";
            // 
            // label5
            // 
            resources.ApplyResources(this.label5, "label5");
            this.label5.Name = "label5";
            // 
            // btnCalib
            // 
            resources.ApplyResources(this.btnCalib, "btnCalib");
            this.btnCalib.Name = "btnCalib";
            this.btnCalib.UseVisualStyleBackColor = true;
            this.btnCalib.Click += new System.EventHandler(this.CalibBtn_Click);
            // 
            // Calibrate
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.btnCalib);
            this.Controls.Add(this.txtMass);
            this.Controls.Add(this.btnInject);
            this.Controls.Add(this.txtVol);
            this.Controls.Add(this.cmbAddress);
            this.Controls.Add(this.label5);
            this.Controls.Add(this.label4);
            this.Controls.Add(this.label3);
            this.Controls.Add(this.label2);
            this.Controls.Add(this.label1);
            this.Name = "Calibrate";
            this.Load += new System.EventHandler(this.Calibrate_Load);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.ComboBox cmbAddress;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.TextBox txtVol;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Button btnInject;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.TextBox txtMass;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Button btnCalib;
    }
}