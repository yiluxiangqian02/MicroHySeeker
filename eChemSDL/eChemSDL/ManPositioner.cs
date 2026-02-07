using System;
using System.Collections.Generic;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class ManPositioner : Form
    {
        public ManPositioner()
        {
            InitializeComponent();
        }

        private class AxisSetting
        {
            public string name { get; set; }
            public string max { get; set; }
            public string cm { get; set; }
            public string pulses { get; set; }
        }

        private void ManPositioner_Load(object sender, EventArgs e)
        {
            if (string.IsNullOrEmpty(LIB.ThePositioner.Port))
            {
                MessageBox.Show("请先在设置里指定样品平台对应的端口，然后重启程序以生效。", "未指定样品平台端口");
                Close();
            }


            List<AxisSetting> axisSettings = new List<AxisSetting>();
            AxisSetting axisSettingX = new AxisSetting();
            AxisSetting axisSettingY = new AxisSetting();
            AxisSetting axisSettingZ = new AxisSetting();


            axisSettingX.name = "X";
            axisSettingX.max = (LIB.ThePositioner.MaxCol + 1).ToString();
            axisSettingX.cm = LIB.ThePositioner.cmperCol.ToString();
            axisSettingX.pulses = LIB.ThePositioner.PulsepercmX.ToString();
            axisSettingY.name = "Y";
            axisSettingY.max = (LIB.ThePositioner.MaxRow + 1).ToString();
            axisSettingY.cm = LIB.ThePositioner.cmperRow.ToString();
            axisSettingY.pulses = LIB.ThePositioner.PulsepercmY.ToString();
            axisSettingZ.name = "Z";
            axisSettingZ.max = (LIB.ThePositioner.MaxLay + 1).ToString();
            axisSettingZ.cm = LIB.ThePositioner.cmperLay.ToString();
            axisSettingZ.pulses = LIB.ThePositioner.PulsepercmZ.ToString();

            axisSettings.Add(axisSettingX);
            axisSettings.Add(axisSettingY);
            axisSettings.Add(axisSettingZ);

            dataGridView1.DataSource = axisSettings;
            lblPort.Text = LIB.ThePositioner.Port;
            lblSpeed.Text = LIB.ThePositioner.Speed.ToString();
            txtRow.Text = (LIB.ThePositioner.Row + 1).ToString();
            txtCol.Text = (LIB.ThePositioner.Col + 1).ToString();
            txtLay.Text = (LIB.ThePositioner.Lay + 1).ToString();

            LIB.ThePositioner.SerialCommunication += Positioner_SerialCommunication;
        }

        private void Positioner_SerialCommunication(object sender, Positioner.SerialCommunicationEventArgs e)
        {
            if (e.Operation == Positioner.SerialCommType.read)
                SetMsgbox(e.Data, " " + LIB.NamedStrings["Receive"] + " ");
                
            if (e.Operation == Positioner.SerialCommType.write)
                SetMsgbox(e.Data, " " + LIB.NamedStrings["Send"] + " ");

        }

        private void SetMsgbox(string command, string sendOrReceive)
        {
            // InvokeRequired required compares the thread ID of the  
            // calling thread to the thread ID of the creating thread.  
            // If these threads are different, it returns true.  
            // 如果是不同线程调用，则通过平台的Invoke方法传递
            if (this.txtMsg.InvokeRequired)
            {
                //SendText的参数是实际操作的函数的名字，实现了把SendText传递给代理函数，然后代理函数被触发

                //之前是DelegateSendText d = new DelegateSendText(SetMsgbox);
                //测试过，用DelegateSendText d = SetMsgbox;也可以运行，应该是一样的，后面其他几个都是这样直接赋值的，没有new。
                DelegateSendText d = SetMsgbox;

                //将delegate函数作为参数传递
                this.Invoke(d, new object[] { command, sendOrReceive });
            }
            else
            {
                this.txtMsg.Text += DateTime.Now + sendOrReceive + command + "\r\n"; // + "[" + String.Join(";", SharedComponents.ThePositioner.CommandBuffer) + "]\r\n"; ;
                this.txtMsg.SelectionStart = this.txtMsg.Text.Length;
                this.txtMsg.ScrollToCaret();

                //下面这段放在这里是为了防止产生线程访问冲突。
                if (LIB.ThePositioner.Busy)
                {
                    DisableButtons();
                }
                else if (!btnMove.Enabled)
                {
                    EnableButtons();
                    UpdateDisplay();//只在移动完之后更新一次界面，否则每次刷新信息就更新会把用户输入的值取代了，这里按钮的可用状态用于保存更新状态
                }
            }
        }

        public void DisableButtons()
        {
            btnMove.Enabled = false;
            btnNext.Enabled = false;
            btnZero.Enabled = false;
            btnPickNext.Enabled = false;
        }

        public void EnableButtons()
        {
            btnMove.Enabled = true;
            btnNext.Enabled = true;
            btnZero.Enabled = true;
            btnPickNext.Enabled = true;
        }

        private void btnMove_Click(object sender, EventArgs e)
        {
            int row, col, lay;
            bool legal = true;
            if (!int.TryParse(txtRow.Text, out row))
            {
                MessageBox.Show("X请输入正确数值！");
                legal = false;
            }
            if (!int.TryParse(txtCol.Text, out col))
            {
                MessageBox.Show("Y请输入正确数值！");
                legal = false;
            }
            if (!int.TryParse(txtLay.Text, out lay))
            {
                MessageBox.Show("Z请输入正确数值！");
                legal = false;
            }
            if (legal)
                LIB.ThePositioner.ToPosition(row - 1, col - 1, lay - 1);
        }

        private void btnReset_Click(object sender, EventArgs e)
        {
            UpdateDisplay();
        }

        private void UpdateDisplay()
        {
            txtRow.Text = (LIB.ThePositioner.Row + 1).ToString();
            txtCol.Text = (LIB.ThePositioner.Col + 1).ToString();
            txtLay.Text = (LIB.ThePositioner.Lay + 1).ToString();
        }

        private void btnSendCmd_Click(object sender, EventArgs e)
        {
            string cmd = txtCmd.Text;
            LIB.ThePositioner.SendCommand(cmd);
        }

        private void ManPositioner_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (LIB.ThePositioner.Busy && LIB.ThePositioner.Live)
            {
                MessageBox.Show(LIB.NamedStrings["HWBusy"]);
                e.Cancel = true;
            }
            else
                LIB.ThePositioner.SerialCommunication -= Positioner_SerialCommunication;
        }

        private void btnZero_Click(object sender, EventArgs e)
        {
            LIB.ThePositioner.ZeroAll();
        }

        private void btnNext_Click(object sender, EventArgs e)
        {
            LIB.ThePositioner.Next();
        }

        private void btnPickNext_Click(object sender, EventArgs e)
        {
            LIB.ThePositioner.NextPickAndPlace();
        }
    }
    public delegate void DelegateSendText(string command, string sendOrReceive);
}
