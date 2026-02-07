using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Configuration;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class Tester : Form
    {
        public Tester()
        {
            InitializeComponent();
        }

        private void Test_Load(object sender, EventArgs e)
        {
            foreach(SettingsProperty sp in Properties.Settings.Default.Properties)
            {
                if (!sp.IsReadOnly)
                    usersettings.Items.Add(sp.Name);
            }
            cmbType.SelectedIndex = 0;
        }

        private void Clear_Click(object sender, EventArgs e)
        {
            foreach(string setting in usersettings.SelectedItems)
            {
                Properties.Settings.Default[setting] = "";
            }
        }

        private void usersettings_SelectedIndexChanged(object sender, EventArgs e)
        {
            foreach (string setting in usersettings.SelectedItems)
            {
                testMsg.Text += setting + ":" + Properties.Settings.Default[setting] + "\r\n------------------------\r\n";
            }
        }

        private void btnFloat_Click(object sender, EventArgs e)
        {
            float numberf;
            double numberd;
            decimal numberc;
            numberf = Convert.ToSingle(txtFloat.Text);
            numberd = numberf;
            
            numberc = Convert.ToDecimal(numberf);
            if (cmbType.SelectedIndex == 0)
                testMsg.Text += numberf.ToString() + "\r\n";
            if (cmbType.SelectedIndex == 1)
                testMsg.Text += ((float)numberd).ToString() + "\r\n";
            if (cmbType.SelectedIndex == 2)
                testMsg.Text += numberc.ToString() + "\r\n";
        }

        private void txtFloat_TextChanged(object sender, EventArgs e)
        {

        }
    }
}
