using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.IO.Ports;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class RS485调试 : Form
    {
        MotorRS485 motorRS485;
        byte[] Speed_SpdMode, Speed_PosMode;
        readonly string[] HardVersion_E = { "Unknown HardVer", "MKS SERVO42E_485", "MKS SERVO42E_CAN", "MKS SERVO57E_485", "MKS SERVO57E_CAN", "MKS SERVO28E_485", "MKS SERVO28E_CAN", "MKS SERVO35E_485", "MKS SERVO35E_CAN" };
        readonly string[] HardVersion_D = { "Unknown HardVer", "MKS SERVO42D_485", "MKS SERVO42D_CAN", "MKS SERVO57D_485", "MKS SERVO57D_CAN", "MKS SERVO28D_485", "MKS SERVO28D_CAN", "MKS SERVO35D_485", "MKS SERVO35D_CAN" };
        string[] HardVersion;
        string HV, FV;
        byte[] FV1 = new byte[] { 0, 0, 0 };


        public RS485调试()
        {
            InitializeComponent();
        }

        private void Form1_Load(object sender, EventArgs e)
        {
            motorRS485 = LIB.RS485Driver;
            GB4_3_comboBox_速度档位.Text = "100";//速度档位
            GB4_4_comboBox_速度档位.Text = "100";//速度档位
            GB4_4_textBox_脉冲数.Text = "4000";//脉冲数
            GB4_4_comboBox_模式切换.Text = "绝对编码";//脉冲数模式
            GB4_3_radioButton_正转.Checked = true;
            GB4_4_radioButton_正转.Checked = true;
            motorRS485.OnMessageReceived += Motor_DataReceived;
            foreach (string s in LIB.RS485Driver.GetAddressStr())
            {
                GB1_comboBox_通讯地址.Items.Add(s);
            }
            GB1_comboBox_通讯地址.SelectedIndex = 0;
        }


        

        private void Motor_DataReceived(byte[] data)
        {
            // Convert response to hex string and show in a TextBox or Console
            string hex = BitConverter.ToString(data);
            if (data[0] == 0xFB && data[2] == 0x40)
            {
                try
                {
                    if ((data[3] & 0x80) == 0x80)
                    {
                        HardVersion = HardVersion_E;
                    }
                    else
                    {
                        HardVersion = HardVersion_D;
                    }
                    if ((data[3] & 0x0f) <= 8 && (data[3] & 0x0f) >= 1)
                    {
                        HV = HardVersion[data[3] & 0x0f];
                    }
                    else
                    {
                        HV = HardVersion[0];
                    }
                    FV = "V" + data[4] + "." + data[5] + "." + data[6];
                    for (int a = 0; a < 3; a++)
                    {
                        FV1[a] = data[a + 4];
                    }
                    if (HardVersion == HardVersion_E)
                    {
                        MessageBox.Show("检测到当前电机为ServoE系列，请使用MKS ServoE Control上位机。", "警告");
                    }
                    MessageBox.Show("硬件版本" + ":  " + HV + "\n" + "固件版本" + ":  " + FV, "Version");

                }
                catch
                {
                    MessageBox.Show("返回信息不够长度。", "错误");
                }
            }
            Invoke((Action)(() =>
            {
                GB6_textBox_数据日志.AppendText($"[{DateTime.Now:HH:mm:ss.fff}] 接收: {hex}{Environment.NewLine}");
            }));
        }


        private void GB4_3_button_开始_Click(object sender, EventArgs e)
        {
            ushort Speed;
            Speed = Convert.ToUInt16(GB4_3_comboBox_速度档位.Text, 10);
            motorRS485.RunSpeedModeAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16), Speed, GB4_3_radioButton_正转.Checked).ContinueWith(t =>
            {
                if (t.IsFaulted)
                {
                    MessageBox.Show("运行失败: " + t.Exception.InnerException.Message, "错误");
                }
            });
        }

        private void GB4_3_button_停止_Click(object sender, EventArgs e)
        {
            motorRS485.StopSpeedModeAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16)).ContinueWith(t =>
            {
                if (t.IsFaulted)
                {
                    MessageBox.Show("停止失败: " + t.Exception.InnerException.Message, "错误");
                }
            });
        }

        private void GB4_4_button_开始_Click(object sender, EventArgs e)
        {
            motorRS485.RunRelativePositionModeAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16), Convert.ToInt32(GB4_4_textBox_脉冲数.Text), Convert.ToUInt16(GB4_4_comboBox_速度档位.Text, 10), GB4_4_radioButton_正转.Checked).ContinueWith(t =>
            {
                if (t.IsFaulted)
                {
                    MessageBox.Show("运行失败: " + t.Exception.InnerException.Message, "错误");
                }
                else
                {
                    byte[] sentCommand = t.Result;
                    string hex = BitConverter.ToString(sentCommand);
                    Invoke((MethodInvoker)(() =>
                    {
                        GB6_textBox_数据日志.AppendText($"[{DateTime.Now:HH:mm:ss.fff}] 发送: {hex}{Environment.NewLine}");
                    }));
                }
            });
        }

        private void btnReadSubdiv_Click(object sender, EventArgs e)
        {
            motorRS485.ReadAllSettingsAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16));
        }

        private void btnReadStatus_Click(object sender, EventArgs e)
        {
            motorRS485.ReadAllStatusAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16));
        }

        private void btnRunstate_Click(object sender, EventArgs e)
        {
            motorRS485.GetRunStatusAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16));
        }

        private void RS485调试_FormClosing(object sender, FormClosingEventArgs e)
        {
            motorRS485.OnMessageReceived -= Motor_DataReceived;
        }

        private async void btnReadversion_Click(object sender, EventArgs e)
        {
            try
            {
                await motorRS485.GetVersionAsync(addr: Convert.ToByte(GB1_comboBox_通讯地址.Text, 16)).ContinueWith(t =>
                {
                    if (t.IsFaulted)
                    {
                        MessageBox.Show("读取版本失败: " + t.Exception.InnerException.Message, "错误");
                    }
                    else
                    {
                        byte[] sentCommand = t.Result;
                        string hex = BitConverter.ToString(sentCommand);
                        Invoke((MethodInvoker)(() =>
                        {
                            GB6_textBox_数据日志.AppendText($"[{DateTime.Now:HH:mm:ss.fff}] 发送: {hex}{Environment.NewLine}");
                        }));
                    }
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error: " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void GB4_4_button_停止_Click(object sender, EventArgs e)
        {
            motorRS485.StopRelativePositionModeAsync(Convert.ToByte(GB1_comboBox_通讯地址.Text, 16)).ContinueWith(t =>
            {
                if (t.IsFaulted)
                {
                    MessageBox.Show("停止失败: " + t.Exception.InnerException.Message, "错误");
                }
            });
        }
    }
}