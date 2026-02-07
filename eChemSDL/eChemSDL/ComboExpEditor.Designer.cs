namespace eChemSDL
{
    partial class ComboExpEditor
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(ComboExpEditor));
            this.groupBox2 = new System.Windows.Forms.GroupBox();
            this.StepList = new System.Windows.Forms.ListBox();
            this.GroupBoxParam = new System.Windows.Forms.GroupBox();
            this.btnClose = new System.Windows.Forms.Button();
            this.btnSavechanges = new System.Windows.Forms.Button();
            this.btnSaveRun = new System.Windows.Forms.Button();
            this.lblInfo = new System.Windows.Forms.Label();
            this.MsgBox = new System.Windows.Forms.TextBox();
            this.btnDisplayMatrix = new System.Windows.Forms.Button();
            this.directoryEntry1 = new System.DirectoryServices.DirectoryEntry();
            this.groupBox2.SuspendLayout();
            this.SuspendLayout();
            // 
            // groupBox2
            // 
            resources.ApplyResources(this.groupBox2, "groupBox2");
            this.groupBox2.Controls.Add(this.StepList);
            this.groupBox2.Name = "groupBox2";
            this.groupBox2.TabStop = false;
            // 
            // StepList
            // 
            resources.ApplyResources(this.StepList, "StepList");
            this.StepList.DrawMode = System.Windows.Forms.DrawMode.OwnerDrawVariable;
            this.StepList.FormattingEnabled = true;
            this.StepList.Name = "StepList";
            this.StepList.DrawItem += new System.Windows.Forms.DrawItemEventHandler(this.StepList_DrawItem);
            this.StepList.MeasureItem += new System.Windows.Forms.MeasureItemEventHandler(this.StepList_MeasureItem);
            // 
            // GroupBoxParam
            // 
            resources.ApplyResources(this.GroupBoxParam, "GroupBoxParam");
            this.GroupBoxParam.Name = "GroupBoxParam";
            this.GroupBoxParam.TabStop = false;
            // 
            // btnClose
            // 
            resources.ApplyResources(this.btnClose, "btnClose");
            this.btnClose.DialogResult = System.Windows.Forms.DialogResult.Cancel;
            this.btnClose.Name = "btnClose";
            this.btnClose.UseVisualStyleBackColor = false;
            this.btnClose.Click += new System.EventHandler(this.btnClose_Click);
            // 
            // btnSavechanges
            // 
            resources.ApplyResources(this.btnSavechanges, "btnSavechanges");
            this.btnSavechanges.Name = "btnSavechanges";
            this.btnSavechanges.UseVisualStyleBackColor = true;
            this.btnSavechanges.Click += new System.EventHandler(this.btnSavechanges_Click);
            // 
            // btnSaveRun
            // 
            resources.ApplyResources(this.btnSaveRun, "btnSaveRun");
            this.btnSaveRun.DialogResult = System.Windows.Forms.DialogResult.OK;
            this.btnSaveRun.Name = "btnSaveRun";
            this.btnSaveRun.UseVisualStyleBackColor = true;
            this.btnSaveRun.Click += new System.EventHandler(this.btnSaveRun_Click);
            // 
            // lblInfo
            // 
            resources.ApplyResources(this.lblInfo, "lblInfo");
            this.lblInfo.Name = "lblInfo";
            // 
            // MsgBox
            // 
            resources.ApplyResources(this.MsgBox, "MsgBox");
            this.MsgBox.BackColor = System.Drawing.SystemColors.Control;
            this.MsgBox.Name = "MsgBox";
            this.MsgBox.ReadOnly = true;
            // 
            // btnDisplayMatrix
            // 
            resources.ApplyResources(this.btnDisplayMatrix, "btnDisplayMatrix");
            this.btnDisplayMatrix.Name = "btnDisplayMatrix";
            this.btnDisplayMatrix.UseVisualStyleBackColor = true;
            this.btnDisplayMatrix.Click += new System.EventHandler(this.btnDisplayMatrix_Click);
            // 
            // ComboExpEditor
            // 
            resources.ApplyResources(this, "$this");
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.Controls.Add(this.btnDisplayMatrix);
            this.Controls.Add(this.MsgBox);
            this.Controls.Add(this.lblInfo);
            this.Controls.Add(this.btnClose);
            this.Controls.Add(this.GroupBoxParam);
            this.Controls.Add(this.btnSavechanges);
            this.Controls.Add(this.btnSaveRun);
            this.Controls.Add(this.groupBox2);
            this.Name = "ComboExpEditor";
            this.Load += new System.EventHandler(this.ComboExpEditor_Load);
            this.groupBox2.ResumeLayout(false);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.GroupBox groupBox2;
        private System.Windows.Forms.ListBox StepList;
        private System.Windows.Forms.GroupBox GroupBoxParam;
        private System.Windows.Forms.Button btnClose;
        private System.Windows.Forms.Button btnSavechanges;
        private System.Windows.Forms.Button btnSaveRun;
        private System.Windows.Forms.Label lblInfo;
        private System.Windows.Forms.TextBox MsgBox;
        private System.Windows.Forms.Button btnDisplayMatrix;
        private System.DirectoryServices.DirectoryEntry directoryEntry1;
    }
}