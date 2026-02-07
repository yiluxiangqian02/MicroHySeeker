using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class Degas : Form
    {
        private TableLayoutPanel tlp = new TableLayoutPanel();

        public Degas()
        {
            InitializeComponent();
        }

        private void Degas_Load(object sender, EventArgs e)
        {
            SuspendLayout();
            Label desc = new Label();
            desc.AutoSize = true;
            desc.Text = LIB.NamedStrings["PrimeDesc"];//"快速推拉针筒除气泡，活塞应先退后以防碰撞。";
            desc.MaximumSize = new Size(300, 0);
            desc.TextAlign = ContentAlignment.MiddleLeft;
            desc.Anchor = AnchorStyles.Bottom | AnchorStyles.Left;
            tlp.Controls.Add(desc, 0, 0);
            tlp.SetColumnSpan(desc, 2);

            for (int i = 0; i < LIB.CHs.Count; i++)
            {
                Label channellabel = new Label();
                CheckBox activechannel = new CheckBox();
                channellabel.AutoSize = true;
                activechannel.AutoSize = true;
                activechannel.Text = "[" + (i + 1).ToString() + "] " + LIB.CHs[i].ChannelName + " " + LIB.NamedStrings["Sol"] + " ";
                channellabel.Text = LIB.NamedStrings["Conc"] + ": " + LIB.CHs[i].HighConc.ToString() + "/L ";
                channellabel.Text += LIB.NamedStrings["PumpAddress"] + ": " + LIB.CHs[i].Address;
                channellabel.TextAlign = ContentAlignment.MiddleLeft;
                channellabel.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left;
                activechannel.Name = LIB.CHs[i].ChannelName;

                tlp.Controls.Add(activechannel, 0, i + 1);
                tlp.Controls.Add(channellabel, 1, i + 1);
            }

            //tlp.Dock = DockStyle.Fill;
            tlp.AutoSize = true;
            tlp.Left = 10;
            tlp.Top = 10;
            Controls.Add(tlp);
            ResumeLayout();
        }

        private void btnSelAll_Click(object sender, EventArgs e)
        {
            foreach(Control ctl in tlp.Controls)
            {
                if (ctl is CheckBox)
                    ((CheckBox)ctl).Checked = true;
            }
        }

        private void btnSelNone_Click(object sender, EventArgs e)
        {
            foreach (Control ctl in tlp.Controls)
            {
                if (ctl is CheckBox)
                    ((CheckBox)ctl).Checked = false;
            }
        }

        private void btnDegas_Click(object sender, EventArgs e)
        {
            int i = 0;
            foreach (Control ctl in tlp.Controls)
            {
                if (ctl is CheckBox)
                {
                    if(((CheckBox)ctl).Checked == true)
                    {
                        /*LIB.Diluters[i].Initialize(LIB.CHs[i]);
                        LIB.Diluters[i].Syringespd = 99.0;//注意此处修改了针筒速度！但是在之后的程序中每次使用针筒都有初始化，所以没影响
                        LIB.Diluters[i].FwdCycleDur = LIB.Diluters[i].CycleLen / 99.0 * 60 * 1000;//这个也是
                        double vol;
                        vol = Math.PI * LIB.Diluters[i].SyringeDia * LIB.Diluters[i].SyringeDia / 4000 * LIB.Diluters[i].CycleLen;
                        LIB.Diluters[i].AddSolvent(vol);*/
                        LIB.Diluters[i].Prepare(0.0, true, 50.0); //准备除气泡，实际不注入液体
                        LIB.Diluters[i].Infuse(); //执行除气泡
                    }
                    i++;
                }
            }
        }
    }
}
