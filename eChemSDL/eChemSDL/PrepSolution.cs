using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class PrepSolution : Form
    {
        private GroupBox solcontainer = new GroupBox();
        private TableLayoutPanel tlpsol = new TableLayoutPanel();

        public PrepSolution()
        {
            InitializeComponent();
            string Json;
            Json = Properties.Settings.Default.LConcs;
            if (!string.IsNullOrEmpty(Json))
            {
                List<SingleSolution> lcs = JsonConvert.DeserializeObject<List<SingleSolution>>(Json);
                foreach (SingleSolution lc in lcs)
                {
                    LConcs.Add(lc);
                }

            }
        }



        public string solvent { get; set; }

        public List<SingleSolution> LConcs = new List<SingleSolution>();

        private void MakeSolution_Load(object sender, EventArgs e)
        {
            SuspendLayout();
            solcontainer.Text = LIB.NamedStrings["SolRcp"];// "溶液配方";
            solcontainer.AutoSize = true;

            Label totalVollbl = new Label();
            TextBox totalVolinput = new TextBox();
            totalVollbl.Text = LIB.NamedStrings["TotalVol"];// "总体积（mL）:";
            totalVollbl.AutoSize = true;
            totalVollbl.TextAlign = ContentAlignment.MiddleLeft;
            totalVollbl.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
            totalVolinput.Text = LIB.MixedSol.TotalVol.ToString();
            totalVolinput.Name = "TotalVol";
            totalVolinput.Width = 40;

            for (int i = 0; i < LIB.CHs.Count; i++)
            {
                Label channellabel = new Label();
                Label lowConclabel = new Label();
                TextBox lowConcinput = new TextBox();
                RadioButton isSolvent = new RadioButton();
                //channellabel.Text = "[" + SharedComponents.CHs[i].ChannelName + "溶液,源浓度:" + "" + SharedComponents.CHs[i].HighConc.ToString() + "/L 端口:" + SharedComponents.CHs[i].PortName + "]";
                channellabel.Text = "[" + LIB.CHs[i].ChannelName + " " + LIB.NamedStrings["Source"] + " " + LIB.NamedStrings["Conc"] + ": " + LIB.CHs[i].HighConc.ToString() + "/L " + LIB.NamedStrings["Port"] + ": " + LIB.CHs[i].Address + "]";
                lowConclabel.Text = LIB.NamedStrings["LowConc"];// "目标浓度(/L):";
                SingleSolution lc = LConcs.FirstOrDefault(plc => plc.Solute == LIB.CHs[i].ChannelName);
                if (lc != null)
                {
                    lowConcinput.Text = lc.LowConc.ToString();
                    if (lc.IsSolvent == true)
                        isSolvent.Checked = true;
                }
                lowConcinput.Name = i.ToString();
                isSolvent.Name = i.ToString();
                isSolvent.Text = LIB.NamedStrings["IsSolvent"];//"这是溶剂";
                isSolvent.CheckedChanged += IsSolvent_CheckedChanged;
                channellabel.AutoSize = true;
                lowConclabel.AutoSize = true;
                lowConcinput.Width = 40;


                tlpsol.Controls.Add(channellabel, 0, i);
                tlpsol.Controls.Add(lowConclabel, 1, i);
                tlpsol.Controls.Add(lowConcinput, 2, i);
                tlpsol.Controls.Add(isSolvent, 3, i);
            }

            tlpsol.Controls.Add(totalVollbl, 1, LIB.CHs.Count);
            tlpsol.Controls.Add(totalVolinput, 2, LIB.CHs.Count);

            tlpsol.Dock = DockStyle.Fill;
            tlpsol.AutoSize = true;
            solcontainer.Controls.Add(tlpsol);
            Controls.Add(solcontainer);
            ResumeLayout();
        }

        private void IsSolvent_CheckedChanged(object sender, EventArgs e)
        {
            foreach (Control ctl in tlpsol.Controls.Find(((RadioButton)sender).Name, true))
            {
                if (ctl is TextBox)
                {
                    if (((RadioButton)sender).Checked)
                        ctl.Enabled = false;
                    else
                        ctl.Enabled = true;
                }

            }
        }

        private void startMake_Click(object sender, EventArgs e)
        {
            LConcs.Clear();
            SingleSolution lc;
            foreach (Control ctl in tlpsol.Controls)
            {
                if (ctl.Name == "TotalVol")
                    LIB.MixedSol.TotalVol = Convert.ToDouble(ctl.Text);

                else if (ctl is TextBox)
                {
                    if (!string.IsNullOrEmpty(ctl.Text))
                        lc = new SingleSolution(Convert.ToInt32(ctl.Name), Convert.ToDouble(ctl.Text), false);
                    else
                        lc = new SingleSolution(Convert.ToInt32(ctl.Name), 0.0, false);
                    LConcs.Add(lc);
                }
            }
            foreach (Control ctl in tlpsol.Controls)
            {
                if (ctl is RadioButton)
                {
                    if (((RadioButton)ctl).Checked)
                    {
                        //Solvent = ctl.Name;
                        LConcs[Convert.ToInt32(ctl.Name)].IsSolvent = true;
                    }
                }
            }
            string Json;
            Json = JsonConvert.SerializeObject(LConcs);
            Properties.Settings.Default.LConcs = Json;
            Properties.Settings.Default.Save();
        }
    }


}
