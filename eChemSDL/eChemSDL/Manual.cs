using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.IO.Ports;
using System.Threading;
using eChemSDL;

namespace COMtest
{
    public partial class Manualwindow : Form
    {
        public Manualwindow()
        {
            InitializeComponent();
        }

        private void Form_Load(object sender, EventArgs e)
        {
            foreach (Diluter dl in LIB.Diluters)
            {
                cmbChannelList.Items.Add(dl.Name);
                cmbChannelList.SelectedIndex = 0;
                spdunitCmb.SelectedIndex = 1;
            }
        }

        private void stopBtn_Click(object sender, EventArgs e)
        {
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).Stop();
        }

        private void runBtn_Click(object sender, EventArgs e)
        {
            int unit, inspd, outspd;
            double factor;
            inspd = Decimal.ToInt32(speedBox.Value);
            unit = spdunitCmb.SelectedIndex;
            factor = 1;
            if (unit == 0)
                factor = 60;
            if (unit == 2)
                factor = 1.0 / 60;//without the .0 after 1 it will get zero always
            outspd = (int)Math.Round(inspd * 100 * factor, 0);
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).Forward(outspd);
        }

        delegate void sendtext(string text);

        private void setMsgbox(string text)
        {
            // InvokeRequired required compares the thread ID of the  
            // calling thread to the thread ID of the creating thread.  
            // If these threads are different, it returns true.  
            if (this.testMsgbox.InvokeRequired)
            {
                sendtext d = new sendtext(setMsgbox);
                this.Invoke(d, new object[] { text });
            }
            else
            {
                this.testMsgbox.Text += DateTime.Now + " " + LIB.NamedStrings["Receive"] + " " + text + "\r\n";
                this.testMsgbox.SelectionStart = this.testMsgbox.Text.Length;
                this.testMsgbox.ScrollToCaret();
            }
        }

        private void DataReceivedHandler(object sender,SerialDataReceivedEventArgs e)
        {
            byte[] returnByte = new byte[7];
            SerialPort sp = (SerialPort)sender;
            if(sp.BytesToRead == 7)
            {
                sp.Read(returnByte, 0, 7);
                setMsgbox(BitConverter.ToString(returnByte).Replace("-", string.Empty));
            }
        }

        private void frevBtn_MouseDown(object sender, MouseEventArgs e)
        {
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).FastRewind();
        }

        private void frevBtn_MouseUp(object sender, MouseEventArgs e)
        {
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).Stop();
        }

        private void ffBtn_MouseDown(object sender, MouseEventArgs e)
        {
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).FastForward();
        }

        private void ffBtn_MouseUp(object sender, MouseEventArgs e)
        {
            //LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).Stop();
        }


        private void portsList_SelectedIndexChanged(object sender, EventArgs e)
        {
            //lblPort.Text = LIB.Diluters.SingleOrDefault(dl => dl.Name == cmbChannelList.Text).Port;
        }
    }
}
