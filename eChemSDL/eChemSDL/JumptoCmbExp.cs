using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class JumptoCmbExp : Form
    {
        public int CmbIndex = 1;
        public int MaxCmbIndex = 10000;


        public JumptoCmbExp()
        {
            InitializeComponent();
        }

        private void JumptoCmbExp_Load(object sender, EventArgs e)
        {
            numCmbIndex.Value = CmbIndex;
            numCmbIndex.Maximum = MaxCmbIndex;
            if (!LIB.LastExp.ComboParamsValid())
                btnRunSelected.Enabled = false;
        }

        private void btnJumptoCmbExp_Click(object sender, EventArgs e)
        {
            CmbIndex = Decimal.ToInt32(numCmbIndex.Value);
        }

        private void btnRunSelected_Click(object sender, EventArgs e)
        {
            Button btnSender = (Button)sender;
            EnterSelected selectexp = new EnterSelected();

            Point ptTopLeft = new Point(0, -selectexp.Height - 10);
            ptTopLeft = this.PointToScreen(ptTopLeft);
            selectexp.Location = ptTopLeft;
            DialogResult dlgResult;
            dlgResult = selectexp.ShowDialog();
            if(dlgResult == DialogResult.OK)
            {

            }
        }
    }
}
