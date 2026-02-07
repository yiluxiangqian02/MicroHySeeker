using Newtonsoft.Json;
using System;
using System.IO.Ports;
using System.Linq;
using System.Windows.Forms;
using System.Windows.Markup;


namespace eChemSDL
{
    public partial class ManMotorsOnRS485 : Form
    {
        private MotorRS485 Controller;

        public ManMotorsOnRS485()
        {
            InitializeComponent();
            Controller = LIB.RS485Driver;
            //Serialport = new SerialPort();

            //RS485Controller.SettingsReady += Motor_SettingsReady;
            //SerialCommunication是自定义的马达模块的事件，在这里用于和调用程序之间传递信息，不操作串口。
            //如果不需要监视马达模块的通讯信息，这句是不需要的（测试过，可以运行，只是信息没显示，因为没有被截获）
            Controller.OnMessageReceived += Motor_SerialCommunication;
        }

        private void Motor_SerialCommunication(byte[] message)
        {
            string hex = BitConverter.ToString(message);
            SetMsgbox($"[{DateTime.Now:HH:mm:ss.fff}] {LIB.NamedStrings["Receive"]}: {hex}{Environment.NewLine}");
        }

        private void ManMotorsOnRS485_Load(object sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(Properties.Settings.Default.RS485Port))
            {
                MessageBox.Show("请先在设置里指定冲洗通道对应的端口，然后重启程序以生效。", "未指定冲洗通道");
                Close();
            }
            //RS485Controller已经初始化了，直接使用就行了。
            //else
            //{
            //    Controller.Initialize();
            //}
            lblCom.Text = Properties.Settings.Default.RS485Port;
        }

        //参数里的sendOrReceive只是一个字符串，不限定值，这里为了简单起见在调用时直接用常数字符串来填充
        //这个函数不是马达模块中的，但是由于调用者需要在马达模块发生通讯事件时得到通知，为马达模块实现了SerialCommunication事件，这样事件返回的参数和调用者
        //位于不同的线程，所以通过了代理函数。
        //C#中回调函数一个是可以通过代理函数（用变量存储函数指针），另一个方法是使用接口对象（使用接口的对象的成员函数），网上查的。
        //因为调用者要读马达信息时，要等待马达返回，所以要用回调；同时马达又要等串口返回，又是另一层回调，一共2层。
        
        private void SetMsgbox(string message)
        {
            if (this.testMsgbox.InvokeRequired)
            {
                DelegateSendMsg d = SetMsgbox;
                this.Invoke(d, new object[] { message });
            }
            else
            {
                this.testMsgbox.AppendText(message);
                this.testMsgbox.SelectionStart = this.testMsgbox.Text.Length;
                this.testMsgbox.ScrollToCaret();
            }
        }


        public void ShowMotorSettings()
        {
            string Settings;
            Settings = JsonConvert.SerializeObject(Controller.MotorList);
            MessageBox.Show(Settings);
        }

        private void buttonCWCont_Click(object sender, EventArgs e)
        {
            Controller.CWRun(Convert.ToByte(addressbox.Text, 16), Convert.ToUInt16(speedBox.Text, 10));
        }

        private void buttonCCWRunCont_Click(object sender, EventArgs e)
        {
            Controller.CCWRun(Convert.ToByte(addressbox.Text, 16), Convert.ToUInt16(speedBox.Text, 10));
        }

        private void buttonStop_Click(object sender, EventArgs e)
        {
            Controller.Stop(Convert.ToByte(addressbox.Text, 16));
        }

        private void buttonSend_Click(object sender, EventArgs e)
        {
            string hex;
            hex = textBoxCommand.Text.Replace(" ", "");
            if ((hex.Length % 2) != 0)
                hex += " ";
            byte[] Bytes = new byte[hex.Length / 2];
            for (int i = 0; i < Bytes.Length; i++)
                Bytes[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
            Controller.SendCommand(Bytes);
        }

        private void btnSetAddr_Click(object sender, EventArgs e)
        {
            if (MessageBox.Show("确认更改电机地址？（更改后请在电机上做好标记）", "确认更改地址", MessageBoxButtons.YesNo) == DialogResult.Yes)
            {
                //if (!Controller.ChangeAddress(Decimal.ToInt16(addressbox.Value)))
                    MessageBox.Show("不实现在这里更改电机地址功能");
            }
        }

        //private void btnCheckCmd_Click(object sender, EventArgs e)
        //{
        //    MessageBox.Show("[" + String.Join(";", Controller.CommandBuffer) + "]\r\n");
        //}

        private void MotorsOnRS485Panel_FormClosing(object sender, FormClosingEventArgs e)
        {
            //RS485Controller.SerialCommunication -= Motor_SerialCommunication;
            //if(RS485Controller.CommandBuffer.Count > 0)
            //{
            //    MessageBox.Show("命令缓冲区未清空，请过几秒钟后再关闭窗口。");
            //    e.Cancel = true;
            //}
            //else
                Controller.DetachDataReader();
        }
    }
    //声明代理函数SendText，感觉代理函数就像是在圈子外面的一个围观者，通过它可以临时取代任何一个圈子内的参数，防止循环调用的线程冲突。
    //这里定义两个代理函数类型，它们不是函数本身，函数本身是一个变量。
    //代理函数用法，首先，定义函数类型和参数表；其次，实例化，即用该函数类型声明一个变量，并将其指向一个普通函数；最后，用该函数类型的变量进行调用。
    public delegate void DelegateSendMsg(string message);
}
