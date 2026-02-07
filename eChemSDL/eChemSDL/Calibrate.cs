using System;
using System.IO.Ports;
using System.Linq;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class Calibrate : Form
    {
        public Calibrate()
        {
            InitializeComponent();
        }

        private void Calibrate_Load(object sender, EventArgs e)
        {
            // Safely get address strings; handle null or empty result
            var addresses = LIB.RS485Driver.GetAddressStr() ?? Enumerable.Empty<string>();
            var addrArray = addresses.ToArray();

            if (addrArray.Length > 0)
            {
                cmbAddress.Items.AddRange(addrArray);
                cmbAddress.SelectedIndex = 0;
            }
            else
            {
                // No addresses found — disable actions that depend on a selected address
                btnInject.Enabled = false;
                btnCalib.Enabled = false;
                // Optional: inform the user (uncomment if desired)
                // MessageBox.Show("未发现可用地址，请检查 RS485 驱动或连接。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void injectBtn_Click(object sender, EventArgs e)
        {
            double vol;
            Diluter diluter; // = new Diluter();
            foreach (Diluter dl in LIB.Diluters)
            {
                Console.WriteLine(dl.Address.ToString("X2") + " " + dl.Name);
            }
            try
            {
                vol = Convert.ToDouble(txtVol.Text);
                diluter = LIB.Diluters.SingleOrDefault(dl => dl.Address == Convert.ToByte(cmbAddress.Text,16));
                Console.WriteLine(Convert.ToByte(cmbAddress.Text, 16).ToString());
                Console.WriteLine("Diluter: " + diluter?.Address.ToString("X2") + " " + diluter?.Name);
                if (diluter != null)
                {
                    diluter.Prepare(0.0, true, vol);
                    diluter.Infuse();//TODO: 添加完成通知，让用户去称重
                }
            }
            catch (FormatException)
            {
                MessageBox.Show(LIB.NamedStrings["WrongVolFormat"], LIB.NamedStrings["WrongFormat"], MessageBoxButtons.OK);
            }
            catch (OverflowException)
            {
                MessageBox.Show(LIB.NamedStrings["OutOfRangeLong"], LIB.NamedStrings["OutOfRange"], MessageBoxButtons.OK);
            }
        }

        private void CalibBtn_Click(object sender, EventArgs e)
        {
            double setvol;
            double realvol;
            try
            {
                setvol = Convert.ToDouble(txtVol.Text);
                realvol = Convert.ToDouble(txtMass.Text);
                LIB.ChannelSettings ch;
                ch = LIB.CHs.SingleOrDefault(dl => dl.Address == Convert.ToByte(cmbAddress.Text,16));
                if (ch != null)
                {
                    int oldDivpermL = ch.DivpermL;
                    ch.DivpermL = (int)(realvol / setvol * oldDivpermL);
                }
            }
            catch (FormatException)
            {
                MessageBox.Show(LIB.NamedStrings["WrongVolFormat"], LIB.NamedStrings["WrongFormat"], MessageBoxButtons.OK);
            }
            catch (OverflowException)
            {
                MessageBox.Show(LIB.NamedStrings["OutOfRangeLong"], LIB.NamedStrings["OutOfRange"], MessageBoxButtons.OK);
            }
        }
    }
}
