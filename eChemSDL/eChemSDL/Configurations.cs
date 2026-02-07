using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO.Ports;
using System.Resources;
using System.Threading;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class Configurations : Form
    {
        //private class channelsetting
        //{
        //    public string channelname { get; set; }
        //    public double highConc { get; set; }
        //    public double syringeDiameter { get; set; }
        //    public double syringeSpeed { get; set; }
        //    public double cycleL { get; set; }
        //    public string portname { get; set; }
        //}


        //static BindingList<ChannelSettings> CHs = new BindingList<ChannelSettings>();
        //static BindingSource CHsettingsSource = new BindingSource(CHs, null);

        public bool LanguageChanged = false;
        public int CultureSelected;

        public Configurations()
        {

            InitializeComponent();
            ResourceManager rm = new ResourceManager(typeof(UserStrings));
            //CultureInfo newCulture = new CultureInfo((cmbLanguages.SelectedItem as dynamic).Value);

            Properties.Settings.Default.Save();

            foreach (string s in SerialPort.GetPortNames())
            {
                cmbPortPos.Items.Add(s);
                cmb485Port.Items.Add(s);
                //portsList.SelectedIndex = portsList.Items.Count - 1;
            }
            cmbPortPos.Items.Add(rm.GetString("None"));
            cmb485Port.Items.Add(rm.GetString("None"));
            cmbPortPos.Text = LIB.ThePositioner.Port;
            cmb485Port.Text = Properties.Settings.Default.RS485Port;

            ChannelGridView.AutoGenerateColumns = false;
            ChannelGridView.DataSource = LIB.CHsettingsSource;
            PPGridView.AutoGenerateColumns = false;
            PPGridView.DataSource = LIB.PPSettingsSource;

            solvateColorview.AutoGenerateColumns = false;

            DataGridViewComboBoxColumn diluteraddressColumn = (DataGridViewComboBoxColumn)ChannelGridView.Columns["AddressDiluter"];
            diluteraddressColumn.Items.Add(rm.GetString("None"));
            DataGridViewComboBoxColumn flusheraddressColumn = (DataGridViewComboBoxColumn)PPGridView.Columns["AddressFlusher"];
            flusheraddressColumn.Items.Add(rm.GetString("None"));

            // 遍历在线的电机地址，并且包含配置中已有的地址，避免 DataGridViewComboBoxCell 值无效
            Dictionary<string, byte> pumpAddresses = new Dictionary<string, byte>();
            var detected = LIB.RS485Driver?.GetAddressStr() ?? new string[0];
            foreach (string s in detected)
            {
                byte parsed;
                if (byte.TryParse(s, out parsed))
                {
                    string key = parsed.ToString("D2");
                    if (!pumpAddresses.ContainsKey(key))
                        pumpAddresses.Add(key, parsed);
                }
            }
            // 包含当前配置中保存的通道地址，防止下拉列表中缺失已有值导致异常
            foreach (var ch in LIB.CHs)
            {
                string key = ch.Address.ToString("D2");
                if (!pumpAddresses.ContainsKey(key))
                    pumpAddresses.Add(key, ch.Address);
            }
            // 同时包含冲洗泵设置里的地址
            foreach (var pp in LIB.PPs)
            {
                string key = pp.Address.ToString("D2");
                if (!pumpAddresses.ContainsKey(key))
                    pumpAddresses.Add(key, pp.Address);
            }
            // 添加一个空地址，表示不使用电机
            if (!pumpAddresses.ContainsKey(rm.GetString("None")))
                pumpAddresses.Add(rm.GetString("None"), 255);

            diluteraddressColumn.DataPropertyName = "Address";
            diluteraddressColumn.DataSource = new BindingSource(pumpAddresses, null);
            diluteraddressColumn.DisplayMember = "Key";
            diluteraddressColumn.ValueMember = "Value";

            flusheraddressColumn.DataPropertyName = "Address";
            flusheraddressColumn.DataSource = new BindingSource(pumpAddresses, null);
            flusheraddressColumn.DisplayMember = "Key";
            flusheraddressColumn.ValueMember = "Value";
            //添加保存的电机地址（注意：不一定在线，先取消这段吧）
            //foreach (LIB.ChannelSettings ch in LIB.CHs)
            //{
            //    if (!addressColumn.Items.Contains(ch.Address))
            //        addressColumn.Items.Add(ch.Address);
            //}

            //设置蠕动泵参数
            DataGridViewComboBoxColumn DirectionColumn = (DataGridViewComboBoxColumn)PPGridView.Columns["Direction"];

            //下面这段只是为了把enum类型中的Description字段作为显示项,传递参数时仍然是enum数据类型,连int都不行!搞了很久才通过
            Dictionary<string, LIB.PeriPumpSettings.PumpDirection> MotorDirections = new Dictionary<string, LIB.PeriPumpSettings.PumpDirection>();
            foreach (LIB.PeriPumpSettings.PumpDirection enumValue in Enum.GetValues(typeof(LIB.PeriPumpSettings.PumpDirection)))
            {
                MotorDirections.Add(enumValue.GetDescription(), enumValue);//GetDescription()是自定义在MainWin.cs的静态函数，可全局调用
            }

            DirectionColumn.DataSource = new BindingSource(MotorDirections, null);
            DirectionColumn.DisplayMember = "Key";
            DirectionColumn.ValueMember = "Value";
            //以上
            DirectionColumn.DataPropertyName = "Direction";

            if (!LIB.EngineeringMode)
            {
                tabControl.TabPages.Remove(tabDisplay);//
                //tabControl.TabPages.Remove(tabGeneral);
            }
            //如果没有RS485端口，则不显示通道设置和冲洗设置
            if (!LIB.AvailablePorts.Contains(Properties.Settings.Default.RS485Port))
            {
                tabControl.TabPages.Remove(tabChannel);
                tabControl.TabPages.Remove(tabFlush);
            }

            cmbLanguages.Items.Clear();
            cmbLanguages.Items.Add(new { Text = rm.GetString("Chinese"), Value = "zh" });
            cmbLanguages.Items.Add(new { Text = rm.GetString("English"), Value = "en" });
            cmbLanguages.DisplayMember = "Text";
            cmbLanguages.ValueMember = "Value";            //cmbLanguages.SelectedIndex = 0;
            cmbLanguages.DataSource = cmbLanguages.Items;//虽然很奇怪，但是必须设置DataSource属性才能够设置SelectedValue，否则SelectedValue永远是null
            cmbLanguages.SelectedValue = Thread.CurrentThread.CurrentUICulture.Name.Substring(0, 2);
            CultureSelected = cmbLanguages.SelectedIndex;
            ChannelGridView.TopLeftHeaderCell.Value = rm.GetString("Channel");
            txtDataPath.Text = Properties.Settings.Default.DataFilePath;
            chkStopOnError.Checked = Properties.Settings.Default.StopOnPanic;

            //三轴平台
            txtcmRow.Text = LIB.ThePositioner.cmperRow.ToString();
            txtcmCol.Text = LIB.ThePositioner.cmperCol.ToString();
            txtcmLay.Text = LIB.ThePositioner.cmperLay.ToString();
            txtpulseX.Text = LIB.ThePositioner.PulsepercmX.ToString();
            txtpulseY.Text = LIB.ThePositioner.PulsepercmY.ToString();
            txtpulseZ.Text = LIB.ThePositioner.PulsepercmZ.ToString();
            txtrowCnt.Text = (LIB.ThePositioner.MaxRow + 1).ToString();
            txtcolCnt.Text = (LIB.ThePositioner.MaxCol + 1).ToString();
            txtlayCnt.Text = (LIB.ThePositioner.MaxLay + 1).ToString();
            txtSpeed.Text = LIB.ThePositioner.Speed.ToString();
            txtPickHeight.Text = LIB.ThePositioner.PickHeight.ToString();
        }

        //public void Initialize()
        //{
        //    ChannelSettings ch;
        //    char ChannelName = 'A';
        //    Point groupTL = new Point(0, 20);
        //    ch = new ChannelSettings();
        //    foreach (string s in SerialPort.GetPortNames())
        //    {
        //        ch.PortName = s;
        //        ch.ChannelName = ChannelName.ToString();
        //        ch.SyringeDiameter = 10.0;
        //        ch.SyringeSpeed = 50.0;
        //        ch.CycleLen = 50.0;
        //        CHs.Add(ch);
        //        tabGen.SuspendLayout();
        //        Label portnamelabel = new Label();
        //        Label channelnamelabel = new Label();
        //        Label syringeDiameterlabel = new Label();
        //        Label syringeSpeedlabel = new Label();
        //        Label cycleLlabel = new Label();
        //        TextBox channelnameinput = new TextBox();
        //        TextBox syringeDiameterinput = new TextBox();
        //        TextBox syringeSpeedinput = new TextBox();
        //        TextBox cycleLinput = new TextBox();
        //        portnamelabel.Text = ch.PortName + "端口:";
        //        channelnamelabel.Text = "溶液名称";
        //        syringeDiameterlabel.Text = "针筒内径(mm)";
        //        syringeSpeedlabel.Text = "注射泵速度(mm/min)";
        //        cycleLlabel.Text = "注射泵行程(mm)";
        //        channelnameinput.Text = ch.ChannelName;
        //        channelnameinput.Name = s;
        //        syringeDiameterinput.Text = ch.SyringeDiameter.ToString();
        //        syringeDiameterinput.Name = s;
        //        syringeSpeedinput.Text = ch.SyringeSpeed.ToString();
        //        syringeSpeedinput.Name = s;
        //        cycleLinput.Text = ch.CycleLen.ToString();
        //        cycleLinput.Name = s;

        //        groupTL.Offset(0, 3);
        //        portnamelabel.Location = groupTL;
        //        portnamelabel.Size = new Size(60, 20);

        //        groupTL.Offset(80, 0);
        //        channelnamelabel.Location = groupTL;
        //        channelnamelabel.Size = new Size(60, 20);

        //        groupTL.Offset(120, -3);
        //        channelnameinput.Location = groupTL;
        //        channelnameinput.Size = new Size(50, 20);

        //        groupTL.Offset(120, 3);
        //        syringeDiameterlabel.Location = groupTL;
        //        syringeDiameterlabel.Size = new Size(80, 20);

        //        groupTL.Offset(120, -3);
        //        syringeDiameterinput.Location = groupTL;
        //        syringeDiameterinput.Size = new Size(50, 20);

        //        groupTL.Offset(-360, 33);
        //        syringeSpeedlabel.Location = groupTL;
        //        syringeSpeedlabel.Size = new Size(120, 20);

        //        groupTL.Offset(120, -3);
        //        syringeSpeedinput.Location = groupTL;
        //        syringeSpeedinput.Size = new Size(50, 20);

        //        groupTL.Offset(120, 3);
        //        cycleLlabel.Location = groupTL;
        //        cycleLlabel.Size = new Size(120, 20);

        //        groupTL.Offset(120, -3);
        //        cycleLinput.Location = groupTL;
        //        cycleLinput.Size = new Size(50, 20);


        //        tabGen.Controls.Add(portnamelabel);
        //        tabGen.Controls.Add(channelnamelabel);
        //        tabGen.Controls.Add(channelnameinput);
        //        tabGen.Controls.Add(syringeDiameterlabel);
        //        tabGen.Controls.Add(syringeDiameterinput);
        //        tabGen.Controls.Add(syringeSpeedlabel);
        //        tabGen.Controls.Add(syringeSpeedinput);
        //        tabGen.Controls.Add(cycleLlabel);
        //        tabGen.Controls.Add(cycleLinput);

        //        tabGen.ResumeLayout(false);
        //        tabGen.PerformLayout();
        //        groupTL.Offset(-440, 50);
        //        ChannelName++;
        //    }
        //}

        private void Configurations_Load(object sender, EventArgs e)
        {
            //MessageBox.Show(Thread.CurrentThread.CurrentUICulture.Name.Substring(0,2));
            //SharedComponents.ChannelSettings ch;
            //char ChannelName = 'A';
            ////Point groupTL = new Point(0, 20);

            //foreach (string s in SerialPort.GetPortNames())
            //{
            //    ch = new SharedComponents.ChannelSettings();
            //    ch.PortName = s;
            //    ch.ChannelName = ChannelName.ToString();
            //    ch.SyringeDiameter = 10.0;
            //    ch.SyringeSpeed = 50.0;
            //    ch.CycleLen = 50.0;
            //    ch.HighConc = 1.0;
            //    SharedComponents.CHs.Add(ch);
            //    ChannelName++;
            //}
            //下面代码不起作用
            //foreach (DataGridViewRow row in ChannelGridView.Rows)
            //{
            //    row.HeaderCell.Value = String.Format("{0}", row.Index + 1);
            //}
            updategrid();
        }

        private void save_Click(object sender, EventArgs e)
        {
            //TODO:输入校验
            string Json;
            Json = JsonConvert.SerializeObject(LIB.CHs);
            Properties.Settings.Default.ChannelListJSON = Json;
            Json = JsonConvert.SerializeObject(LIB.PPs);
            Properties.Settings.Default.FlushingPumpsJSON = Json;
            Properties.Settings.Default.DataFilePath = txtDataPath.Text;
            Properties.Settings.Default.RS485Port = cmb485Port.Text;
            Properties.Settings.Default.StopOnPanic = chkStopOnError.Checked;

            //三轴平台的设置，暂时不用了
            LIB.ThePositioner.Port = cmbPortPos.Text;
            LIB.ThePositioner.Speed = Convert.ToInt32(string.IsNullOrEmpty(txtSpeed.Text) ? "20000" : txtSpeed.Text);
            if (LIB.ThePositioner.Speed > 80000)
                LIB.ThePositioner.Speed = 80000;
            else if (LIB.ThePositioner.Speed < 0)
                LIB.ThePositioner.Speed = 20000;

            LIB.ThePositioner.PulsepercmX = Convert.ToInt32(string.IsNullOrEmpty(txtpulseX.Text) ? "15000" : txtpulseX.Text);
            LIB.ThePositioner.PickHeight = Convert.ToInt32(string.IsNullOrEmpty(txtPickHeight.Text) ? "1" : txtPickHeight.Text);
            if (chkSamepulse.Checked)
            {
                LIB.ThePositioner.PulsepercmY = LIB.ThePositioner.PulsepercmX;
                LIB.ThePositioner.PulsepercmZ = LIB.ThePositioner.PulsepercmX;
            }
            else
            {
                LIB.ThePositioner.PulsepercmY = Convert.ToInt32(string.IsNullOrEmpty(txtpulseY.Text) ? "15000" : txtpulseY.Text);
                LIB.ThePositioner.PulsepercmZ = Convert.ToInt32(string.IsNullOrEmpty(txtpulseZ.Text) ? "15000" : txtpulseZ.Text);
            }

            LIB.ThePositioner.cmperRow = Convert.ToDouble(string.IsNullOrEmpty(txtcmRow.Text) ? "1" : txtcmRow.Text);
            if (chkSamecm.Checked)
            {
                LIB.ThePositioner.cmperCol = LIB.ThePositioner.cmperRow;
                LIB.ThePositioner.cmperLay = LIB.ThePositioner.cmperRow;
            }
            else
            {
                LIB.ThePositioner.cmperCol = Convert.ToDouble(string.IsNullOrEmpty(txtcmCol.Text) ? "1" : txtcmCol.Text);
                LIB.ThePositioner.cmperLay = Convert.ToDouble(string.IsNullOrEmpty(txtcmLay.Text) ? "1" : txtcmLay.Text);
            }

            LIB.ThePositioner.MaxRow = Convert.ToInt32(string.IsNullOrEmpty(txtrowCnt.Text) ? "8" : txtrowCnt.Text) - 1;
            if (chkSameCnt.Checked)
            {
                LIB.ThePositioner.MaxCol = LIB.ThePositioner.MaxRow;
                LIB.ThePositioner.MaxLay = LIB.ThePositioner.MaxRow;
            }
            else
            {
                LIB.ThePositioner.MaxCol = Convert.ToInt32(string.IsNullOrEmpty(txtcolCnt.Text) ? "8" : txtcolCnt.Text) - 1;
                LIB.ThePositioner.MaxLay = Convert.ToInt32(string.IsNullOrEmpty(txtlayCnt.Text) ? "8" : txtlayCnt.Text) - 1;
            }
            Json = JsonConvert.SerializeObject(LIB.ThePositioner);
            Properties.Settings.Default.PositionerJSON = Json;
            if (LIB.AvailablePorts.Contains(LIB.ThePositioner.Port))
                LIB.ThePositioner.Connect();
            if (LIB.AvailablePorts.Contains(Properties.Settings.Default.RS485Port))
                LIB.RS485Driver.Initialize();

            string prompt = "";
            string title = "";
            ResourceManager rm = new ResourceManager(typeof(UserStrings));
            try
            {
                CultureInfo newCulture = new CultureInfo((cmbLanguages.SelectedItem as dynamic).Value);
                prompt = rm.GetString("SettingsSavedandClose", newCulture);
                title = rm.GetString("Notice", newCulture);
                Thread.CurrentThread.CurrentCulture = newCulture;
                Thread.CurrentThread.CurrentUICulture = newCulture;
                Properties.Settings.Default.Culture = newCulture.Name;
            }
            catch (CultureNotFoundException error)
            {
                Console.WriteLine("Unable to instantiate culture {0}", error.InvalidCultureName);
            }
            //MessageBox.Show(cmbLanguages.SelectedValue.ToString());
            Properties.Settings.Default.Save();

            if (MessageBox.Show(prompt, title, MessageBoxButtons.YesNo) == DialogResult.Yes)
                Close();
        }

        private void cancel_Click(object sender, EventArgs e)
        {
            Close();
        }


        private void updategrid()
        {
            foreach (DataGridViewRow row in ChannelGridView.Rows)
            {
                if (row.Index < LIB.CHs.Count)
                    row.Cells["ChannelColor"].Style.BackColor = LIB.CHs[row.Index].ChannelColor;//没有选中的页面无法在窗口Load时初始化.
            }
        }
        private void tabControl_SelectedIndexChanged(object sender, EventArgs e)
        {
            updategrid();
        }

        //private void solvateColorview_CellContentClick(object sender, DataGridViewCellEventArgs e)
        //{
        //    var senderGrid = (DataGridView)sender;
        //    solvateColorview.ClearSelection();
        //    if (senderGrid.Columns[e.ColumnIndex] is DataGridViewButtonColumn && e.RowIndex >= 0)
        //    {
        //        //TODO - Button Clicked - Execute Code Here
        //        ColorDialog cld = new ColorDialog();
        //        cld.AnyColor = true;
        //        cld.SolidColorOnly = false;
        //        cld.Color = SharedComponents.solcols[e.RowIndex].ChannelColor;

        //        if (cld.ShowDialog() == DialogResult.OK)
        //            SharedComponents.solcols[e.RowIndex].ChannelColor = cld.Color;
        //    }
        //    updategrid();

        //}

        private void Delete_Click(object sender, EventArgs e)
        {
            foreach (DataGridViewRow item in ChannelGridView.SelectedRows)
            {
                //ChannelGridView.Rows.RemoveAt(item.Index);
                LIB.CHs.RemoveAt(item.Index);
            }
        }

        private void channelview_CellContentClick(object sender, DataGridViewCellEventArgs e)
        {
            var senderGrid = (DataGridView)sender;
            ChannelGridView.ClearSelection();
            if (senderGrid.Columns[e.ColumnIndex] is DataGridViewButtonColumn && e.RowIndex >= 0)
            {
                //TODO - Button Clicked - Execute Code Here
                ColorDialog cld = new ColorDialog();
                cld.AnyColor = true;
                cld.SolidColorOnly = false;
                cld.Color = LIB.CHs[e.RowIndex].ChannelColor;

                if (cld.ShowDialog() == DialogResult.OK)
                    LIB.CHs[e.RowIndex].ChannelColor = cld.Color;
            }
            updategrid();
        }


        private void btnBrowse_Click(object sender, EventArgs e)
        {
            FolderBrowserDialog fbd = new FolderBrowserDialog();
            fbd.ShowNewFolderButton = true;
            if (fbd.ShowDialog() == DialogResult.OK)
            {
                txtDataPath.Text = fbd.SelectedPath;
                Properties.Settings.Default.DataFilePath = fbd.SelectedPath;
                LIB.DataFilePath = fbd.SelectedPath;
            }
        }

        private void cmbLanguages_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (CultureSelected != cmbLanguages.SelectedIndex)
                LanguageChanged = true;
        }

        private void chkSamepulse_CheckedChanged(object sender, EventArgs e)
        {
            if (chkSamepulse.Checked)
            {
                txtpulseY.Enabled = false;
                txtpulseZ.Enabled = false;
            }
            else
            {
                txtpulseY.Enabled = true;
                txtpulseZ.Enabled = true;
            }
        }

        private void chkSamecm_CheckedChanged(object sender, EventArgs e)
        {
            if (chkSamecm.Checked)
            {
                txtcmCol.Enabled = false;
                txtcmLay.Enabled = false;
            }
            else
            {
                txtcmCol.Enabled = true;
                txtcmLay.Enabled = true;
            }
        }

        private void ChannelGridView_DataError(object sender, DataGridViewDataErrorEventArgs e)
        {
            MessageBox.Show(e.Exception.ToString(), "Data Error");
        }

        private void ChannelGridView_RowPostPaint(object sender, DataGridViewRowPostPaintEventArgs e)
        {
            var grid = sender as DataGridView;
            var rowIdx = (e.RowIndex + 1).ToString();

            var centerFormat = new StringFormat()
            {
                // right alignment might actually make more sense for numbers
                Alignment = StringAlignment.Center,
                LineAlignment = StringAlignment.Center
            };

            var headerBounds = new Rectangle(e.RowBounds.Left, e.RowBounds.Top, grid.RowHeadersWidth, e.RowBounds.Height);
            e.Graphics.DrawString(rowIdx, this.Font, SystemBrushes.ControlText, headerBounds, centerFormat);

        }

        private void PPGridView_CellFormatting(object sender, DataGridViewCellFormattingEventArgs e)
        {
            if (PPGridView.Columns[e.ColumnIndex].Name == "Role")
            {
                if (e.Value is string)
                    e.Value = LIB.NamedStrings[(string)e.Value];
                //e.FormattingApplied = true;
            }
        }
    }
}
