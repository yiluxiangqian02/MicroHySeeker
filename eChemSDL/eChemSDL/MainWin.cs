using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using Newtonsoft.Json;
using System.IO.Ports;
using System.Drawing.Drawing2D;
using COMtest;
using System.IO;
using Microsoft.WindowsAPICodePack.Taskbar;
using System.Threading;
using System.Resources;
using System.Globalization;
using System.Collections;
using KafkaMessage;
using System.Linq;

namespace eChemSDL
{
    public partial class MainWin : Form
    {

        private System.Windows.Forms.Timer timer;
        private int Heartbeat3 = 0;
        private int Heartbeat6 = 0;
        private int Heartbeat50 = 0;
        private bool SetRedraw = false;
        private List<PointF> ChartPoints = new List<PointF>();
        private string StepInfo;
        private string TimeInfo;
        private string ComboInfo;
        private List<string> RemainingVol = new List<string>();
        private Experiment Exp = new Experiment();

        public MainWin()
        {
            CultureInfo newCulture = new CultureInfo(Properties.Settings.Default.Culture);
            Thread.CurrentThread.CurrentCulture = newCulture;
            Thread.CurrentThread.CurrentUICulture = newCulture;
            InitializeComponent();
            LoadNamedStrings();

            string Json;
            List<string> assignedPorts = new List<string>();//已经被安排的端口
            List<byte> occupiedAddresses = new List<byte>();//已经被占用的485地址
            LIB.AvailablePorts = SerialPort.GetPortNames().ToList();
            LIB.RS485Driver = new MotorRS485();
            // 初始化 RS485 驱动并等待完成，防止后续依赖地址列表的初始化（如创建 Channel/Diluter）发生竞态
            try
            {
                LIB.RS485Driver.Initialize().GetAwaiter().GetResult();
            }
            catch (Exception ex)
            {
                // 记录初始化失败但继续执行，后续逻辑会处理无设备情况
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Warning") ? LIB.NamedStrings["Warning"] : "Warning", "RS485 init failed: " + ex.Message);
            }
            LIB.RS485Driver.OnMessageReceived += LIB.DispatchPumpMessage;

            Json = Properties.Settings.Default.ChannelListJSON;
            if (string.IsNullOrEmpty(Json))
                Json = Properties.Settings.Default.DefaultChannels;
            //如果设置过配液通道，从设置里面读取各配液泵的设置
            if (!string.IsNullOrEmpty(Json))
            {
                //这里ch只是个临时变量，把它的数值复制到SharedComponent.CHs里去
                List<LIB.ChannelSettings> ch = JsonConvert.DeserializeObject<List<LIB.ChannelSettings>>(Json);

                foreach (LIB.ChannelSettings chi in ch)
                {
                    chi.DefaultSettings();//防止有些值为0。
                    LIB.CHs.Add(chi);//添加稀释器设置
                    //assignedPorts.Add(chi.PortName);
                    if (!occupiedAddresses.Contains(chi.Address))//如果端口没有被占用
                    {
                        occupiedAddresses.Add(chi.Address);//添加到已分配端口列表
                    }
                    Diluter diluter = new Diluter(chi);//添加实际稀释器
                    LIB.Diluters.Add(diluter);
                }
            }
            //如果没有设置过配液通道，则创建默认的配液通道，保留最后3个地址给移液通道，前面n-3个地址给配液通道
            else
                LIB.CreateDefaultCHs();
            Json = Properties.Settings.Default.FlushingPumpsJSON;
            if (string.IsNullOrEmpty(Json))
                Json = Properties.Settings.Default.DefaultFlushingPumps;
            if (!string.IsNullOrEmpty(Json))
            {
                List<LIB.PeriPumpSettings> pp = JsonConvert.DeserializeObject<List<LIB.PeriPumpSettings>>(Json);
                foreach (LIB.PeriPumpSettings ppi in pp)
                {
                    LIB.PPs.Add(ppi);//添加设置
                }               
            }
            else
                LIB.CreateDefalutPPs();
            
            if (!string.IsNullOrEmpty(Properties.Settings.Default.Flusher485Port))
            {
                assignedPorts.Add(Properties.Settings.Default.Flusher485Port);
            }

            //读取定位平台设置并转化为实例，如果是第一次运行则构造实例
            Json = Properties.Settings.Default.PositionerJSON;
            if (!string.IsNullOrEmpty(Json))
            {
                LIB.ThePositioner = JsonConvert.DeserializeObject<Positioner>(Json);
                LIB.ThePositioner.Connect();
                assignedPorts.Add(LIB.ThePositioner.Port);
            }
            else
                LIB.ThePositioner = new Positioner();
            //LIB.RS485Controller = new MotorsOnRS485();

            LIB.TheFlusher = new Flusher();

            Json = Properties.Settings.Default.LastExp;
            if(!string.IsNullOrEmpty(Json))
            {
                LIB.LastExp = JsonConvert.DeserializeObject < ExpProgram > (Json);
            }

            LIB.MixedSol.TotalVol = Properties.Settings.Default.TotalVol;
            LIB.WorkingElectrolyte.TotalVol = Properties.Settings.Default.TotalVol;


            List<string> unavailablePorts = new List<string>();
            foreach (string s in assignedPorts)
            {
                if(!LIB.AvailablePorts.Contains(s))
                    unavailablePorts.Add(s);
            }
            if (unavailablePorts.Count > 0)
            {
                string warning = LIB.NamedStrings["Port"] + " " + string.Join(",", unavailablePorts) + " " + LIB.NamedStrings["NoConnection"];
                LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"], warning);
            }

            LIB.CHI = new CHInstrument();//注意这个外部dll会占据一个串口，即使没有设置好，所以必须在这行之前其他模块串口要先打开一次
            LIB.DataFilePath = Properties.Settings.Default.DataFilePath;

            //SendInitialStat();
            //SendConstUpdate();
        }

        private void LoadNamedStrings()
        {
            ResourceManager rm = new ResourceManager(typeof(UserStrings));
            ResourceSet resourceSet = rm.GetResourceSet(CultureInfo.CurrentUICulture, true, true);
            LIB.NamedStrings.Clear();
            foreach (DictionaryEntry entry in resourceSet)
                LIB.NamedStrings.Add(entry.Key.ToString(), entry.Value.ToString());
        }

        private void SaveToolStripMenuItem_Click(object sender, EventArgs e)
        {
            SaveFileDialog sfd = new SaveFileDialog();
            sfd.Filter = "txt files (*.txt)|*.txt|All files (*.*)|*.*";
            sfd.FilterIndex = 2;
            sfd.RestoreDirectory = true;
            if (sfd.ShowDialog() == DialogResult.OK)
            {
                File.WriteAllText(sfd.FileName, JsonConvert.SerializeObject(LIB.LastExp));
            }
        }

        private void ConfToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Configurations ConfDlg = new Configurations();
            ConfDlg.ShowDialog();
            if (ConfDlg.LanguageChanged)
            {
                Controls.Clear();
                LoadNamedStrings();
                InitializeComponent();
            }
        }

        private void AboutHTPSolutionToolStripMenuItem_Click(object sender, EventArgs e)
        {
            AboutBox aboutBox = new AboutBox();
            aboutBox.ShowDialog();
        }

        private void CalibrateToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Calibrate calibrate = new Calibrate();
            calibrate.ShowDialog();
        }


        private void DrawCheveron(PaintEventArgs e, SolidBrush brush, Point dip)
        {
            Point tl = new Point(dip.X-10, dip.Y-10);
            Point[] cheveron =
            {
                 new Point(0, 0),
                 new Point(0, 5),
                 new Point(10, 10),
                 new Point(20, 5),
                 new Point(20, 0),
                 new Point(10, 5),
            };
            for (int i = 0; i < cheveron.Length; i++)
            {
                cheveron[i].Offset(tl);
            }
            
            e.Graphics.FillPolygon(brush, cheveron);
        }

        private void DrawSwitchcase(PaintEventArgs e, Point dip)
        {
            GraphicsPath path = new GraphicsPath();
            Pen greyPen = new Pen(Color.Gray,1.5F);
            Point tl = new Point(dip.X - 10, dip.Y - 10);
            path.AddArc(dip.X - 5, dip.Y - 40, 10, 10, 180, 180);
            path.AddArc(dip.X - 5, dip.Y - 20, 10, 10, 0, 180);
            path.CloseFigure();
            e.Graphics.DrawPath(greyPen, path);
        }

        //绘制烧杯内的溶液（颜色）
        private void DrawSolution(PaintEventArgs e, GraphicsPath gp, Point dip, LIB.MixedSolution sol)
        {
            SolidBrush colorBrush = new SolidBrush(Color.Gray);
            double filledvol = 0;
            int filledpercent = 0;

            filledvol = sol.CurrentVol;
            filledpercent = Convert.ToInt32(filledvol / sol.TotalVol * 100);
            Rectangle fill = new Rectangle(dip.X - 50, dip.Y - filledpercent, 100, filledpercent);
            e.Graphics.SetClip(gp);
            colorBrush.Color = sol.SolColor;
            e.Graphics.FillRectangle(colorBrush, fill);
            e.Graphics.ResetClip();

            DrawInfo(e, filledvol.ToString("F0"), colorBrush, new Point(dip.X-10, dip.Y - 120));
        }

        //画烧杯和搅拌子
        private void DrawBeakers(PaintEventArgs e, Point dip)
        {
            GraphicsPath beaker = new GraphicsPath();
            GraphicsPath[] stirrer = new GraphicsPath[3];
            Matrix TranslateMtx = new Matrix();

            SolidBrush solidBrush = new SolidBrush(Color.WhiteSmoke);
            SolidBrush colorBrush = new SolidBrush(Color.FromArgb(128,Color.Blue));

            stirrer[0] = new GraphicsPath();
            stirrer[1] = new GraphicsPath();
            stirrer[2] = new GraphicsPath();
            


            Pen thickPen = new Pen(Color.Black, 5F);
            Pen thinPen = new Pen(Color.DarkGray, 1.5F);
            e.Graphics.DrawLine(thinPen, dip.X - 250, dip.Y + 20, dip.X - 150, dip.Y + 20);
            e.Graphics.DrawLine(thinPen, dip.X - 50, dip.Y + 20, dip.X + 50, dip.Y + 20);

            beaker.AddLine(dip.X + 50, dip.Y, dip.X + 50, dip.Y + 110);
            beaker.AddArc(dip.X + 30, dip.Y + 100, 20, 20, 0, 90);
            beaker.AddLine(dip.X + 40, dip.Y + 120, dip.X - 40, dip.Y + 120);
            beaker.AddArc(dip.X - 50, dip.Y + 100, 20, 20, 90, 90);
            beaker.AddLine(dip.X - 50, dip.Y + 110, dip.X - 50, dip.Y);
            DrawSolution(e, beaker, new Point(dip.X, dip.Y + 120), LIB.WorkingElectrolyte);
            e.Graphics.DrawPath(thickPen, beaker);

            TranslateMtx.Translate(-200, 0);
            beaker.Transform(TranslateMtx);
            stirrer[0].AddArc(dip.X - 190, dip.Y + 100, 10, 10, 270, 180);
            stirrer[0].AddArc(dip.X - 220, dip.Y + 100, 10, 10, 90, 180);
            stirrer[0].CloseFigure();
            stirrer[2].AddArc(dip.X - 200, dip.Y + 95, 10, 10, 225, 180);
            stirrer[2].AddArc(dip.X - 210, dip.Y + 105, 10, 10, 45, 180);
            stirrer[2].CloseFigure();
            stirrer[1].AddArc(dip.X - 210, dip.Y + 95, 10, 10, 135, 180);
            stirrer[1].AddArc(dip.X - 200, dip.Y + 105, 10, 10, 315, 180);
            stirrer[1].CloseFigure();
            DrawSolution(e, beaker, new Point(dip.X - 200, dip.Y + 120), LIB.MixedSol);
            e.Graphics.DrawPath(thickPen, beaker);
            e.Graphics.DrawPath(thinPen, stirrer[Heartbeat3]);
            e.Graphics.FillPath(solidBrush, stirrer[Heartbeat3]);

        }

        private void DrawInfo(PaintEventArgs e, string str, SolidBrush brush, Point loc)
        {
            Font drawFont = new Font("Arial", 10);
            var centerFormat = new StringFormat()
            {
                // right alignment might actually make more sense for numbers
                Alignment = StringAlignment.Center,
                LineAlignment = StringAlignment.Center
            };
            e.Graphics.DrawString(str,drawFont,brush, new Point(loc.X,loc.Y), centerFormat);
        }

        private void DrawProgress(PaintEventArgs e)
        {
            double stepduration;
            List<double> stepdurations = new List<double>();
            int windowwidth;
            int stepwidth = 0;
            double pixelpersec; //pixel per second
            List<int> stepwidths = new List<int>();
            int progress;

            Point startpoint = new Point(0,53);
            Point endpoint = new Point(-2, 53);
            LinearGradientBrush progressBrush = new LinearGradientBrush(new Point(Heartbeat6, Heartbeat6 ), new Point(6 + Heartbeat6, 6 + Heartbeat6), Color.FromArgb(0, 200, 200, 200), Color.FromArgb(0, 200, 200, 200));
            ColorBlend cblend = new ColorBlend(3);
            cblend.Colors = new Color[3] { Color.FromArgb(0, 200, 200, 200), Color.FromArgb(128, 255, 255, 255), Color.FromArgb(0, 200, 200, 200) };
            cblend.Positions = new float[3] { 0f, 0.5f, 1f };
            progressBrush.InterpolationColors = cblend;
            Pen progresspen = new Pen(progressBrush, 6);
            e.Graphics.CompositingMode = CompositingMode.SourceOver;
            windowwidth = Width - 10;
            pixelpersec = windowwidth / Exp.Duration;

            //为什么每次都要算一遍呢，因为窗口可能大小改变了
            foreach(ProgStep ps in Exp.ActiveSteps)
            {
                if (ps.DurUnit == "hr")
                    stepduration = ps.Duration * 3600;
                else if (ps.DurUnit == "min")
                    stepduration = ps.Duration * 60;
                else if (ps.DurUnit == "ms")
                    stepduration = ps.Duration / 1000;
                else
                    stepduration = ps.Duration;
                stepwidth = Convert.ToInt32(pixelpersec * stepduration);
                endpoint.Offset(stepwidth, 0);
                if (ps.OperType == ProgStep.Operation.PrepSol)
                    e.Graphics.DrawLine(new Pen(Color.LightSkyBlue, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                if (ps.OperType == ProgStep.Operation.EChem)
                    e.Graphics.DrawLine(new Pen(Color.LightPink, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                if (ps.OperType == ProgStep.Operation.Flush)
                    e.Graphics.DrawLine(new Pen(Color.PapayaWhip, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                if (ps.OperType == ProgStep.Operation.Blank)
                    e.Graphics.DrawLine(new Pen(Color.Gainsboro, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                if (ps.OperType == ProgStep.Operation.Transfer)
                    e.Graphics.DrawLine(new Pen(Color.LightGreen, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                if (ps.OperType == ProgStep.Operation.Change)
                    e.Graphics.DrawLine(new Pen(Color.DarkGray, 6), startpoint, endpoint);//菜单栏+工具栏高度为50
                startpoint.Offset(stepwidth,0);
                stepwidths.Add(stepwidth);
                stepdurations.Add(stepduration);

            }

            progress = 0;
            for (int i = 0; i < Exp.CurrentStep; i++)
                    progress += stepwidths[i];
            if(Exp.ActiveSteps[Exp.CurrentStep].State.HasFlag(ProgStep.StepState.busy))
            {
                //有时配液阶段时间估计不准，实际超出时，不要画到下一步去。
                if (Exp.ElapsedStepTime.TotalSeconds > stepdurations[Exp.CurrentStep])
                    progress += stepwidths[Exp.CurrentStep];
                else
                    progress += Convert.ToInt32(Exp.ElapsedStepTime.TotalSeconds / stepdurations[Exp.CurrentStep] * stepwidths[Exp.CurrentStep]);
            }

            Pen blackpen = new Pen(Color.Black, 3);
            e.Graphics.DrawLine(progresspen, 0, 53, progress, 53);
            e.Graphics.DrawLine(blackpen, progress, 50, progress, 56);
            StepInfo = LIB.NamedStrings["CurrentStep"] + ": [" + (Exp.CurrentStep + 1).ToString("D3") + "]:" + Exp.ElapsedStepTime.ToString(@"hh\:mm\:ss");
            //string timeinfo = SharedComponents.NamedStrings["TimeProgress"] + ": " + Exp.ElapsedTime.ToString(@"hh\:mm\:ss") + "/" + (TimeSpan.FromSeconds(Exp.Duration)).ToString(@"hh\:mm\:ss");
            TimeInfo = $"{LIB.NamedStrings["TimeProgress"]}: {Exp.ElapsedTime.ToString(@"hh\:mm\:ss")}/{(TimeSpan.FromSeconds(Exp.Duration)).ToString(@"hh\:mm\:ss")} ({LIB.NamedStrings["CurrentExp"]})";

            //e.Graphics.DrawString("当前步骤：[" + (Exp.CurrentStep + 1).ToString("D3") + "]:" + Exp.ElapsedStepTime.ToString(@"hh\:mm\:ss"), new Font("Arial", 10, FontStyle.Bold), new SolidBrush(Color.Blue), 0, tableLayoutPanel1.Top - 40);
            //e.Graphics.DrawString("总体时间：" + Exp.ElapsedTime.ToString(@"hh\:mm\:ss") + "/" + (TimeSpan.FromSeconds(Exp.Duration)).ToString(@"hh\:mm\:ss"), new Font("Arial", 10, FontStyle.Bold), new SolidBrush(Color.Black), 0, tableLayoutPanel1.Top - 20);
            e.Graphics.DrawString(StepInfo, new Font("Arial", 10, FontStyle.Bold), new SolidBrush(Color.Blue), 0, tableLayoutPanel1.Top - 40);
            e.Graphics.DrawString(TimeInfo, new Font("Arial", 10, FontStyle.Bold), new SolidBrush(Color.Black), 0, tableLayoutPanel1.Top - 20);
            //if (stepProgress.SelectedIndex != Exp.currentStep && stepProgress.Items.Count > 0)
            //    stepProgress.SetSelected(Exp.currentStep, true);
            ////绘制时间显示
            //TaskbarManager.Instance.SetProgressState(TaskbarProgressBarState.Normal);
            //TaskbarManager.Instance.SetProgressValue(progress, windowwidth);

            //timedisplay.Text = "[" + (Exp.currentStep + 1).ToString("D3") + "]:" + Exp.ElapsedStepTime.ToString(@"hh\:mm\:ss") + "\r\n";
            //timedisplay.Text += Exp.ElapsedTime.ToString(@"hh\:mm\:ss") + "/" + (TimeSpan.FromSeconds(Exp.Duration)).ToString(@"hh\:mm\:ss");
        }

        private void DrawFlusingLines(PaintEventArgs e, Point dip)
        {
            GraphicsPath[] Tubings = new GraphicsPath[3];
            GraphicsPath[] TubingsInner = new GraphicsPath[3];
            GraphicsPath[] FlushPump = new GraphicsPath[3];

            SolidBrush whiteBrush = new SolidBrush(Color.White);
            SolidBrush grayBrush = new SolidBrush(Color.Gray);
            SolidBrush colorBrush = new SolidBrush(LIB.MixedSol.SolColor);
            SolidBrush pumpOnline = new SolidBrush(Color.DarkGreen);
            SolidBrush activeBrush;
            Pen thickPen = new Pen(LIB.MixedSol.SolColor, 6F);
            Pen midPen = new Pen(Color.Black, 2.5F);
            Pen thinPen = new Pen(Color.Black, 1.5F);
            Pen flowingPen = new Pen(Color.Aqua, 6F);
            flowingPen.DashStyle = DashStyle.Dot;

            Matrix TranslateMtx = new Matrix();
            Matrix[] RotateMtx = new Matrix[6];
            Point[] PumpCenters = new Point[3];
            PumpCenters[0].X = dip.X - 273;
            PumpCenters[0].Y = dip.Y - 20;
            PumpCenters[1].X = dip.X + 73;
            PumpCenters[1].Y = dip.Y - 20;
            PumpCenters[2].X = dip.X - 100;
            PumpCenters[2].Y = dip.Y - 20;

            for (int i = 0; i < 6; i++)
            {
                RotateMtx[i] = new Matrix();
                if (i % 2 == 0)
                    RotateMtx[i].RotateAt(15 * Heartbeat6, PumpCenters[i / 2]);
                else
                    RotateMtx[i].RotateAt(-15 * Heartbeat6, PumpCenters[i / 2]);
            }
                
            //RotateMtx[0].RotateAt(15 * heartbeat6, new Point(dip.X - 273, dip.Y - 20));
            //RotateMtx[1].RotateAt(-15 * heartbeat6, new Point(dip.X - 273, dip.Y - 20));
            //RotateMtx[2].RotateAt(15 * heartbeat6, new Point(dip.X + 73, dip.Y - 20));
            //RotateMtx[3].RotateAt(-15 * heartbeat6, new Point(dip.X + 73, dip.Y - 20));
            //RotateMtx[4].RotateAt(15 * heartbeat6, new Point(dip.X - 100, dip.Y - 20));
            //RotateMtx[5].RotateAt(-15 * heartbeat6, new Point(dip.X - 100, dip.Y - 20));

            Tubings[0] = new GraphicsPath();
            Tubings[1] = new GraphicsPath();
            Tubings[2] = new GraphicsPath();
            TubingsInner[0] = new GraphicsPath();
            TubingsInner[1] = new GraphicsPath();
            TubingsInner[2] = new GraphicsPath();
            FlushPump[0] = new GraphicsPath();
            FlushPump[1] = new GraphicsPath();
            FlushPump[2] = new GraphicsPath();

            //四个转子
            FlushPump[0].AddEllipse(dip.X - 277, dip.Y - 36, 8, 8);
            FlushPump[0].AddEllipse(dip.X - 265, dip.Y - 24, 8, 8);
            FlushPump[0].AddEllipse(dip.X - 277, dip.Y - 12, 8, 8);
            FlushPump[0].AddEllipse(dip.X - 289, dip.Y - 24, 8, 8);
            FlushPump[1] = (GraphicsPath)FlushPump[0].Clone();
            FlushPump[2] = (GraphicsPath)FlushPump[0].Clone();



            //倒U型管
            Tubings[0].AddLine(dip.X - 310, dip.Y + 100, dip.X - 310, dip.Y -10);
            Tubings[0].AddArc(dip.X - 310, dip.Y - 20, 20, 20, 180, 90);
            Tubings[0].AddArc(dip.X - 256, dip.Y - 20, 20, 20, 270, 90);
            Tubings[0].AddLine(dip.X - 236, dip.Y - 10, dip.X - 236, dip.Y + 100);
            TubingsInner[0] = (GraphicsPath)Tubings[0].Clone();
            Tubings[1] = (GraphicsPath)Tubings[0].Clone();
            TubingsInner[1] = (GraphicsPath)Tubings[0].Clone();
            Tubings[0].Widen(thickPen);
            Tubings[1].Widen(thickPen);

            Tubings[2].AddLine(dip.X - 164, dip.Y + 100, dip.X - 164, dip.Y - 10);
            Tubings[2].AddArc(dip.X - 164, dip.Y - 20, 20, 20, 180, 90);
            Tubings[2].AddArc(dip.X - 56, dip.Y - 20, 20, 20, 270, 90);
            Tubings[2].AddLine(dip.X - 36, dip.Y - 10, dip.X -36, dip.Y + 100);
            TubingsInner[2] = (GraphicsPath)Tubings[2].Clone();
            Tubings[2].Widen(thickPen);

            TranslateMtx.Translate(346, 0);
            FlushPump[1].Transform(TranslateMtx);
            Tubings[1].Transform(TranslateMtx);
            TubingsInner[1].Transform(TranslateMtx);
            TranslateMtx.Reset();
            TranslateMtx.Translate(173, 0);
            FlushPump[2].Transform(TranslateMtx);

            /*
            //if (SharedComponents.PPs[0].PumpStatus == MotorsOnRS485.MotorStatus.running)
            //{
            //    if(SharedComponents.TheFlusher.Bidirectional)
            //    {
            //        if(SharedComponents.TheFlusher.CurrentDirection == SharedComponents.PeriPumpSettings.PumpDirection.forward) //evacuate
            //        {
            //            e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(SharedComponents.MixedSol.ChannelColor)), Tubings[0]);
            //            flowingPen.DashOffset = heartbeat6;
            //            flowingPen.Color = SharedComponents.MixedSol.ChannelColor;
            //            e.Graphics.FillEllipse(colorBrush, dip.X - 91, dip.Y - 36, 32, 32);
            //            FlushPump[0].Transform(RotateMtx[2]);

            //        }
            //        if (SharedComponents.TheFlusher.CurrentDirection == SharedComponents.PeriPumpSettings.PumpDirection.reverse) //fill
            //        {
            //            e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(Color.Aqua)), Tubings[0]);
            //            flowingPen.DashOffset = -heartbeat6;
            //            flowingPen.Color = Color.Aqua;
            //            e.Graphics.FillEllipse(new SolidBrush(Color.Aqua), dip.X - 91, dip.Y - 36, 32, 32);
            //            FlushPump[0].Transform(RotateMtx[0]);
            //        }
            //        e.Graphics.DrawPath(flowingPen, TubingsInner[0]);

            //    }
            //    else
            //    {
            //        e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(Color.Aqua)), Tubings[0]);
            //        flowingPen.DashOffset = -heartbeat6;
            //        e.Graphics.DrawPath(flowingPen, TubingsInner[0]);
            //        e.Graphics.FillEllipse(new SolidBrush(Color.Aqua), dip.X - 91, dip.Y - 36, 32, 32);
            //        if(SharedComponents.PPs[0].Direction == SharedComponents.PeriPumpSettings.PumpDirection.forward)
            //            FlushPump[0].Transform(RotateMtx[0]);
            //        if(SharedComponents.PPs[0].Direction == SharedComponents.PeriPumpSettings.PumpDirection.reverse)
            //            FlushPump[0].Transform(RotateMtx[2]);
            //    }
            //}
            //e.Graphics.DrawPath(thinPen, Tubings[0]);
            //Tubings[0].Transform(TranslateMtx);
            //TubingsInner[0].Transform(TranslateMtx);
            //FlushPump[1].Transform(TranslateMtx);

            //if (SharedComponents.PPs[1].PumpStatus == MotorsOnRS485.MotorStatus.running)
            //{
            //    if (SharedComponents.TheFlusher.Bidirectional)
            //    {
            //        if (SharedComponents.TheFlusher.CurrentDirection == SharedComponents.PeriPumpSettings.PumpDirection.forward) //evacuate
            //        {
            //            e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(SharedComponents.MixedSol.ChannelColor)), Tubings[0]);
            //            flowingPen.DashOffset = heartbeat6;
            //            flowingPen.Color = SharedComponents.MixedSol.ChannelColor;
            //            e.Graphics.FillEllipse(colorBrush, dip.X + 59, dip.Y - 36, 32, 32);
            //            FlushPump[1].Transform(RotateMtx[1]);
            //        }
            //        if (SharedComponents.TheFlusher.CurrentDirection == SharedComponents.PeriPumpSettings.PumpDirection.reverse) //fill
            //        {
            //            e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(Color.Aqua)), Tubings[0]);
            //            flowingPen.DashOffset = -heartbeat6;
            //            flowingPen.Color = Color.Aqua;
            //            e.Graphics.FillEllipse(new SolidBrush(Color.Aqua), dip.X + 59, dip.Y - 36, 32, 32);
            //            FlushPump[1].Transform(RotateMtx[3]);
            //        }
            //        e.Graphics.DrawPath(flowingPen, TubingsInner[0]);
            //    }
            //    else
            //    {
            //        e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(SharedComponents.MixedSol.ChannelColor)), Tubings[0]);
            //        flowingPen.DashOffset = heartbeat6;
            //        flowingPen.Color = SharedComponents.MixedSol.ChannelColor;
            //        e.Graphics.DrawPath(flowingPen, TubingsInner[0]);
            //        e.Graphics.FillEllipse(colorBrush, dip.X + 59, dip.Y - 36, 32, 32);
            //        if (SharedComponents.PPs[1].Direction == SharedComponents.PeriPumpSettings.PumpDirection.forward)
            //            FlushPump[1].Transform(RotateMtx[1]);
            //        if (SharedComponents.PPs[1].Direction == SharedComponents.PeriPumpSettings.PumpDirection.reverse)
            //            FlushPump[1].Transform(RotateMtx[3]);
            //    }
            //}
            //e.Graphics.FillPath(colorBrush, Tubings[0]);
            //e.Graphics.DrawPath(thinPen, Tubings[0]);*/

            for (int i = 0; i < 3; i++)
            {
                e.Graphics.DrawPath(thinPen, Tubings[i]);
                //if (LIB.RS485Controller.MotorsOnline)
                //    LIB.TheFlusher.UpdateFlusherPumps();
                if (LIB.RS485Driver.MotorsOnline)
                      LIB.TheFlusher.UpdateFlusherPumps();
                if (LIB.PPs[i].PumpStatus.IsRunning == true)
                {
                    if (LIB.PPs[i].Direction == LIB.PeriPumpSettings.PumpDirection.forward)
                        FlushPump[i].Transform(RotateMtx[2 * i]);
                    if (LIB.PPs[i].Direction == LIB.PeriPumpSettings.PumpDirection.reverse)
                        FlushPump[i].Transform(RotateMtx[2 * i + 1]);
                    Color activecolor;
                    if (i == 1)
                        activecolor = LIB.WorkingElectrolyte.SolColor;
                    else if (i == 2)
                        activecolor = LIB.MixedSol.SolColor;
                    else 
                        activecolor = Color.Aqua;
                    e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(activecolor)), Tubings[i]);
                    flowingPen.DashOffset = Heartbeat6;
                    flowingPen.Color = activecolor;
                    colorBrush.Color = activecolor;
                    e.Graphics.DrawPath(flowingPen, TubingsInner[i]);
                    e.Graphics.FillEllipse(colorBrush, PumpCenters[i].X - 16, PumpCenters[i].Y - 16, 32, 32);
                }
                e.Graphics.FillEllipse(grayBrush, PumpCenters[i].X - 8, PumpCenters[i].Y - 8, 16, 16);
                e.Graphics.DrawEllipse(midPen, PumpCenters[i].X - 16, PumpCenters[i].Y - 16, 32, 32);
                e.Graphics.DrawEllipse(midPen, PumpCenters[i].X - 8, PumpCenters[i].Y - 8, 16, 16);
                e.Graphics.FillPath(grayBrush, FlushPump[i]);
                e.Graphics.DrawPath(midPen, FlushPump[i]);
                if ((i + 1) <= LIB.RS485Driver.MotorList.Count)
                    activeBrush = pumpOnline;
                else
                    activeBrush = grayBrush;
                //                DrawInfo(e, "#" + (i + 1).ToString(), activeBrush, new Point(PumpCenters[i].X - 8, dip.Y));//
                //DrawInfo(e, "#" + (i + 1).ToString(), activeBrush, new Point(PumpCenters[i].X - 8, dip.Y));
                DrawInfo(e, LIB.PPs[i].PumpName + "\r\n# " + LIB.PPs[i].Address.ToString(), activeBrush, new Point(PumpCenters[i].X, dip.Y + 20));
            }
            #region
            ////画左右两个泵体
            ////if (SharedComponents.PPs[0].PumpStatus == MotorsOnRS485.MotorStatus.running)
            ////{
            ////    e.Graphics.FillEllipse(new SolidBrush(Color.Aqua), origin.X - 91, origin.Y - 36, 32, 32);
            ////}
            //e.Graphics.FillEllipse(grayBrush, dip.X - 83, dip.Y - 28, 16, 16);
            //e.Graphics.DrawEllipse(midPen, dip.X - 91, dip.Y - 36, 32, 32);
            //e.Graphics.DrawEllipse(midPen, dip.X - 83, dip.Y - 28, 16, 16);

            ////if (SharedComponents.PPs[1].PumpStatus == MotorsOnRS485.MotorStatus.running)
            ////{
            ////    e.Graphics.FillEllipse(colorBrush, origin.X + 59, origin.Y - 36, 32, 32);
            ////}
            //e.Graphics.FillEllipse(grayBrush, dip.X + 67, dip.Y - 28, 16, 16);
            //e.Graphics.DrawEllipse(midPen, dip.X + 59, dip.Y - 36, 32, 32);
            //e.Graphics.DrawEllipse(midPen, dip.X + 67, dip.Y - 28, 16, 16);

            ////画泵的转子
            ////if(SharedComponents.PPs[0].PumpStatus == MotorsOnRS485.MotorStatus.running)
            ////    FlushPump[0].Transform(RotateMtx[0]);
            //e.Graphics.FillPath(grayBrush, FlushPump[0]);
            //e.Graphics.DrawPath(midPen, FlushPump[0]);
            ////FlushPump[1].Transform(TranslateMtx);
            ////if (SharedComponents.PPs[1].PumpStatus == MotorsOnRS485.MotorStatus.running)
            ////    FlushPump[1].Transform(RotateMtx[1]);
            //e.Graphics.FillPath(grayBrush, FlushPump[1]);
            //e.Graphics.DrawPath(midPen, FlushPump[1]);
            #endregion
            DrawInfo(e, "Cycle: " + LIB.TheFlusher.CycleNumber.ToString(), grayBrush, new Point(PumpCenters[2].X, dip.Y + 40));
        }

        private void DrawCHInstrument(PaintEventArgs e, Point dip)
        {
            GraphicsPath WELead = new GraphicsPath();
            GraphicsPath CELead = new GraphicsPath();
            GraphicsPath RELead = new GraphicsPath();
            GraphicsPath CHIBox = new GraphicsPath();
            AdjustableArrowCap CustomArrow = new AdjustableArrowCap(3, 4);
            CustomArrow.MiddleInset = 1;
            

            Pen staticPen = new Pen(Color.Black, 4F);
            Pen flowingPen = new Pen(Color.AliceBlue,3F);
            flowingPen.DashCap = DashCap.Round;
            flowingPen.DashStyle = DashStyle.Dot;
            Pen activePen;

            //电极线
            //CELead.AddLine(origin.X + 20, origin.Y + 88, origin.X + 20, origin.Y + 72);
            CELead.AddLine(dip.X + 12, dip.Y + 80, dip.X + 28, dip.Y + 80);
            CELead.AddLine(dip.X + 28, dip.Y - 47, dip.X + 160, dip.Y - 47);

            //WELead.AddEllipse(origin.X - 20, origin.Y + 72, 16, 16);
            WELead.AddLine(dip.X - 20, dip.Y + 72, dip.X - 20, dip.Y - 55);
            //WELead.AddLine(dip.X - 30, dip.Y + 30, dip.X + 20, dip.Y + 30);
            WELead.AddLine(dip.X - 20, dip.Y - 55, dip.X + 160, dip.Y - 55);

            RELead.AddLine(dip.X + 160, dip.Y - 51, dip.X + 12, dip.Y - 51);
            RELead.AddLine(dip.X + 12, dip.Y + 47, dip.X - 12, dip.Y + 71);

            //电化学工作站
            CHIBox.AddArc(dip.X + 145, dip.Y - 67, 10, 10,180,90);
            CHIBox.AddArc(dip.X + 250, dip.Y - 67, 10, 10, 270, 90);
            CHIBox.AddArc(dip.X + 250, dip.Y-30, 10, 10, 0, 90);
            CHIBox.AddArc(dip.X + 145, dip.Y-30, 10, 10, 90, 90);
            CHIBox.CloseFigure();
            //if (SharedComponents.PPs[0].PumpStatus == MotorsOnRS485.MotorStatus.running)
            //{
            //    e.Graphics.FillPath(new SolidBrush(ControlPaint.Dark(Color.Aqua)), Tubings[0]);
            //    flowingPen.DashOffset = -heartbeat6;
            //    e.Graphics.DrawPath(flowingPen, TubingsInner[0]);
            //}
            activePen = staticPen;
            activePen.Color = Color.Green;
            e.Graphics.FillEllipse(new SolidBrush(Color.LimeGreen), dip.X - 28, dip.Y + 72, 16, 16);//工作电极头
            e.Graphics.DrawEllipse(activePen, dip.X - 28, dip.Y + 72, 16, 16);//工作电极头
            e.Graphics.DrawPath(activePen, WELead);
            activePen.Color = Color.DarkRed;
            e.Graphics.DrawLine(activePen, dip.X + 12, dip.Y + 88, dip.X + 12, dip.Y + 72);
            e.Graphics.DrawPath(activePen, CELead);
            activePen.Color = Color.Blue;
            activePen.CustomEndCap = CustomArrow;
            e.Graphics.DrawPath(activePen, RELead);
            if (Exp.Running)
            {
                if(Exp.ActiveSteps[Exp.CurrentStep].OperType == ProgStep.Operation.EChem)
                {
                    flowingPen.DashOffset = Heartbeat6;
                    activePen = flowingPen;
                    activePen.Color = ControlPaint.Light(Color.Green);
                    e.Graphics.DrawPath(activePen, WELead);
                    activePen.Color = ControlPaint.Light(Color.DarkRed);
                    e.Graphics.DrawPath(activePen, CELead);
                    lock(LIB.VAPoints)
                    {
                        ChartPoints.Clear();
                        for (int i = 0; i < LIB.VAPoints.Count; i++)
                        {
                            ChartPoints.Add(new PointF(LIB.VAPoints[i].X, LIB.VAPoints[i].Y));
                        }
                        VAChart.DataBind();//刷新图形，直接用SharedComponents.VAPoints来刷新图片会有出现线程冲突现象因为databind用了foreach语句
                    }
                }
            }

            e.Graphics.DrawPath(new Pen(Color.Black, 1.5F), CHIBox);
            e.Graphics.FillPath(new SolidBrush(Color.WhiteSmoke), CHIBox);
            //DrawInfo(e, "电化学工作站", new SolidBrush(Color.Black), new Point(origin.X + 157, origin.Y - 40));
            DrawInfo(e, LIB.NamedStrings["ECStation"], new SolidBrush(Color.Black), new Point(dip.X + 200, dip.Y - 40));

            if (LIB.CHIConnected)
                e.Graphics.FillEllipse(new SolidBrush(Color.LimeGreen), dip.X + 150, dip.Y - 62, 5, 5);
            else
                e.Graphics.FillEllipse(new SolidBrush(Color.Red), dip.X + 150, dip.Y - 62, 5, 5);
        }

        //绘制样品台
        private void DrawPositioner(PaintEventArgs e, Point dip)
        {
            //e.Graphics.DrawRectangle(new Pen(new SolidBrush(Color.Black)), dip.X-150, dip.Y+40, 70, 70);
            int top = dip.Y + 80;
            int left = dip.X - 120;
            int maxrow = LIB.ThePositioner.MaxRow;
            int maxcol = LIB.ThePositioner.MaxCol;
            int maxlay = LIB.ThePositioner.MaxLay;
            int count = (maxrow + 1) * (maxcol + 1);
            bool rearrange=false;
            SolidBrush greenBrush = new SolidBrush(Color.Lime);
            SolidBrush grayBrush = new SolidBrush(Color.DimGray);
            SolidBrush redBrush = new SolidBrush(Color.Red);
            Pen blackpen = new Pen(new SolidBrush(Color.Black));
            if ((maxrow + 1) * (maxcol + 1) <= 225 && maxlay <= 14)//样品数不超过15X15X15就画图
            {
                if (maxcol > 14 || maxrow > 14)
                {
                    maxrow = (maxcol + 1) * (maxrow + 1) / 15;
                    maxcol = 14;
                    rearrange = true;//换算成线性
                }
                for (int y = 0; y <= maxrow; y++)
                {
                    for (int x = 0; x <= maxcol; x++)
                    {
                        if(rearrange)
                        {
                            int index = LIB.ThePositioner.Col + LIB.ThePositioner.Row * (LIB.ThePositioner.MaxCol + 1);
                            int outdex = x + y * 15;
                            if (index == outdex)
                            {
                                if (LIB.ThePositioner.Busy)
                                    e.Graphics.FillRectangle(redBrush, left + 5 * x, top + 5 * y, 4, 4);
                                else
                                    e.Graphics.FillRectangle(greenBrush, left + 5 * x, top + 5 * y, 4, 4);
                            }
                            else if (outdex < count)
                            {
                                e.Graphics.FillRectangle(grayBrush, left + 5 * x, top + 5 * y, 4, 4);
                                if (outdex % (LIB.ThePositioner.MaxCol + 1) == 0)
                                    e.Graphics.DrawRectangle(blackpen, left + 5 * x, top + 5 * y, 4, 4);
                            }

                        }
                        else
                        {
                            if (x == LIB.ThePositioner.Col && y == LIB.ThePositioner.Row)
                            {
                                if (LIB.ThePositioner.Busy)
                                    e.Graphics.FillRectangle(redBrush, left + 5 * x, top + 5 * y, 4, 4);
                                else
                                    e.Graphics.FillRectangle(greenBrush, left + 5 * x, top + 5 * y, 4, 4);
                            }
                            else
                                e.Graphics.FillRectangle(grayBrush, left + 5 * x, top + 5 * y, 4, 4);
                        }
                    }
                }
                top = top + maxlay * 5;
                for (int z = 0; z <= LIB.ThePositioner.MaxLay; z++)
                {
                    if (z == LIB.ThePositioner.Lay)
                    {
                        if (LIB.ThePositioner.Busy)
                            e.Graphics.FillRectangle(redBrush, left + 5 * (maxcol + 2), top - 5 * z, 4, 4);
                        else
                            e.Graphics.FillRectangle(greenBrush, left + 5 * (maxcol + 2), top - 5 * z, 4, 4);
                    }
                        
                    else
                        e.Graphics.FillRectangle(grayBrush, left + 5 * (maxcol + 2), top - 5 * z, 4, 4);
                }
            }
            else//样品数超过就直接显示数量
            {
                string info = $"[{LIB.ThePositioner.Col}/{maxcol},{LIB.ThePositioner.Row}/{maxrow},{LIB.ThePositioner.Lay}/{maxlay}]";
                DrawInfo(e, info, grayBrush, new Point(left, top));
            }
        }

        private void DrawExpApparatus(PaintEventArgs e)
        {
            SolidBrush greyBrush = new SolidBrush(Color.Gray);
            SolidBrush colorBrush;
            Pen colorPen;
            Pen greyPen = new Pen(greyBrush, 6);
            Pen activePen;
            SolidBrush activeBrush;
            string channelinfo;
            string remainingVol;
            bool mixerrunning = false;


            Point origin = new Point(100, 150);
            Point center = new Point();
            Point inject = new Point();
            Point[] manifold =
            {
                new Point(origin.X-10,origin.Y + 86),
                new Point(origin.X+100 * (LIB.Diluters.Count-1)+10,origin.Y + 86)
            };
            center.X = (manifold[1].X + manifold[0].X) / 2;
            center.Y = manifold[0].Y + 6 * (LIB.Diluters.Count - 1) + 20;
            inject.X = center.X - 200;
            inject.Y = center.Y;

            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;

            for(int i = 0; i< LIB.Diluters.Count; i++)
            {
                DrawCheveron(e, greyBrush, inject);
                inject.Offset(0, 10);
            }
            center.Y = inject.Y;
            DrawBeakers(e, center);//
            DrawFlusingLines(e, center);
            DrawCHInstrument(e, center);
            DrawPositioner(e, center);
            VAChart.Left = center.X + 145;
            VAChart.Top = center.Y;
            inject.Offset(0, -10 * LIB.Diluters.Count);

            RemainingVol.Clear();
            for (int i = 0; i< LIB.Diluters.Count; i++)
            {
                bool channelready = false;

                colorBrush = new SolidBrush(LIB.Diluters[i].ChannelColor);
                colorPen = new Pen(colorBrush, 6);

                DrawCheveron(e, greyBrush, origin);
                origin.Offset(0, 8);
                DrawCheveron(e, greyBrush, origin);
                origin.Offset(0, 8);
                DrawCheveron(e, greyBrush, origin);
                origin.Offset(0, -16);
                
                if (!LIB.Diluters[i].isInfusing())
                {
                    activePen = greyPen;
                    activeBrush = greyBrush;
                }
                else
                {
                    mixerrunning = true;
                    activePen = colorPen;
                    activeBrush = colorBrush;
                }

                int offset = i + Heartbeat50 % LIB.Diluters.Count;
                if (offset>=LIB.Diluters.Count)
                    offset = offset - LIB.Diluters.Count;
                inject.Offset(0, 10 * offset);
                if(mixerrunning)
                    DrawCheveron(e, activeBrush, inject);

                inject.Offset(0, -10 * offset);

                origin.Offset(0, 8 * Heartbeat3);
                DrawCheveron(e, activeBrush, origin);
                origin.Offset(0, -8 * Heartbeat3);

                channelinfo = LIB.CHs[i].ChannelName + " (" + LIB.CHs[i].HighConc + "/L)\r\n# " + LIB.CHs[i].Address;
                //TODO:改为遍历电机地址
                foreach (byte addr in LIB.RS485Driver.GetAddressBytes())
                {
                    if (LIB.CHs[i].Address == addr)
                        channelready = true;
                }
                if(channelready)
                    DrawInfo(e, channelinfo, colorBrush, new Point(origin.X, origin.Y - 60));
                else
                    DrawInfo(e, channelinfo, greyBrush, new Point(origin.X, origin.Y - 60));

                if (LIB.Diluters[i].GetRemainingVol() > LIB.Diluters[i].PartVol)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], "配液错误出现了。");
                    LogMsgBuffer.AddEntry(LIB.NamedStrings["Error"], LIB.Diluters[i].GetTestMsg());
                }
                remainingVol = LIB.Diluters[i].GetRemainingVol().ToString("F2") + "\r\n" + LIB.Diluters[i].PartVol.ToString("F2");
                DrawInfo(e, remainingVol, activeBrush, new Point(origin.X-30, origin.Y));

                RemainingVol.Add(remainingVol);


                DrawSwitchcase(e, origin);
                e.Graphics.FillEllipse(activeBrush, origin.X - 5, origin.Y - 30 + (LIB.Diluters[i].isInfusing()?1:0) * 10, 10, 10);

                e.Graphics.DrawLine(activePen, manifold[0], manifold[1]);
                e.Graphics.DrawLine(activePen, new Point(origin.X, origin.Y + 14), new Point(origin.X, manifold[0].Y));

                manifold[0].Y += 6;
                manifold[1].Y += 6;
                origin.Offset(100, 0);
                
            }
            //if (Heartbeat50 == 0)
            //{
            //    LogMsgbox.Text += "\r\n\r\n[" + Exp.ElapsedTime.ToString() + "]" + JsonConvert.SerializeObject(Exp.currentStep);
            //}
        }




        private void MainWin_Paint(object sender, PaintEventArgs e)
        {
            测试用ToolStripMenuItem.Visible = LIB.EngineeringMode;
            if (SetRedraw)
            {
                DrawExpApparatus(e);
            }
            if (Exp.Running)
            {
                DrawProgress(e);
                btnRunSingleExp.Enabled = false;
                btnRunComboExp.Enabled = false;
                btnNextCombo.Enabled = false;
                btnPrevCombo.Enabled = false;
                //btnJumptoCombo.Enabled = false;
                btnResetCombo.Enabled = false;
            }
            else
            {
                btnRunSingleExp.Enabled = true;
                btnRunComboExp.Enabled = true;
                btnNextCombo.Enabled = true;
                btnPrevCombo.Enabled = true;
                //btnJumptoCombo.Enabled = true;
                btnResetCombo.Enabled = true;
            }
            if(Exp.Interim)
            {
                //SendExpStat();
                stepProgress.DataSource = null;
                stepProgress.DataSource = Exp.ActiveSteps;
                Exp.Interim = false;
            }
            ComboInfo = $"{LIB.NamedStrings["ComboExpProgress"]} : {Exp.Program.SelectComboProgress().ToString()} / {Exp.Program.ConstConcExpCount.ToString()} (ID: {Exp.Program.ComboProgress().ToString()}/{Exp.Program.ComboExpCount().ToString()}) ({Exp.ElapsedComboTime.ToString(@"hh\:mm\:ss")})";
            if (Exp.ComboRunning)
                e.Graphics.DrawString(ComboInfo, new Font("Arial", 10, FontStyle.Bold), new SolidBrush(Color.Blue), 0, tableLayoutPanel1.Top - 60);
            else
                e.Graphics.DrawString(ComboInfo, new Font("Arial", 10, FontStyle.Regular), new SolidBrush(Color.Gray), 0, tableLayoutPanel1.Top - 60);
        }

        private void MainWin_Load(object sender, EventArgs e)
        {
            timer = new System.Windows.Forms.Timer();
            timer.Interval = 200;
            timer.Tick += MainTimerEvent;
            timer.Start();
            VAChart.DataSource = ChartPoints;
            Exp.LoadProgram(LIB.LastExp);
            stepProgress.DataSource = Exp.ActiveSteps;
            //SendExpStat();
            MinimumSize = new Size(Width, Height);
        }


        private void MainTimerEvent(Object source, EventArgs e)
        {
            SetRedraw = true;
            if (LogMsgBuffer.HasContent())
            {
                int previouslinenumber = LogMsgbox.Lines.Length;
                int previousend = LogMsgbox.TextLength;
                if (previouslinenumber > 0)
                    previouslinenumber--;//对付开始对话框为空的情况，全空时，行数为0，出现第一条信息，行数变为2（因为每条信息尾部加了换行）
                //LogMsgbox.AppendText(SharedComponents.LogMsg);
                LogMsgbox.AppendText(LogMsgBuffer.GetContent());
                int addedlinenumber = LogMsgbox.Lines.Length - previouslinenumber;
                for (int i = 0; i < addedlinenumber; i++)
                {
                    string line = LogMsgbox.Lines[previouslinenumber + i];
                    LogMsgbox.SelectionStart = previousend;
                    LogMsgbox.SelectionLength = line.Length + 1;
                    previousend += line.Length;
                    if (LogMsgbox.SelectedText.Contains(LIB.NamedStrings["Warning"]))
                    {

                        LogMsgbox.SelectionColor = Color.OrangeRed;
                        //LogMsgbox.SelectionFont = new Font(LogMsgbox.Font, FontStyle.Bold);
                    }
                    else if (line.Contains(LIB.NamedStrings["Error"]))
                    {
                        LogMsgbox.SelectionColor = Color.DarkRed;
                        //LogMsgbox.SelectionFont = new Font(LogMsgbox.Font,FontStyle.Bold);
                        if (Properties.Settings.Default.StopOnPanic)//出现错误时终止实验 //TODO:需要检查是否实验中用到该设备？这个错误只在新信息过来时触发停止
                            Exp.ResetComboStates();
                        //LogMsgbox.SelectionFont = new Font(LogMsgbox.Font, FontStyle.Bold);
                    }
                }
                LogMsgbox.SelectionStart = LogMsgbox.Text.Length;
                LogMsgbox.SelectionLength = 0;
                LogMsgbox.ScrollToCaret();
                //SharedComponents.LogMsg = "";
            }

            if (Heartbeat3 >= 2)
            {
                Heartbeat3 = 0;

                if (Exp.Running)
                {
                    if (stepProgress.SelectedIndex != Exp.CurrentStep && stepProgress.Items.Count > 0)
                        stepProgress.SetSelected(Exp.CurrentStep, true);
                    TaskbarManager.Instance.SetProgressState(TaskbarProgressBarState.Normal);
                    TaskbarManager.Instance.SetProgressValue(Convert.ToInt32(Exp.ElapsedTime.TotalSeconds), Convert.ToInt32(Exp.Duration));

                }
                else
                    TaskbarManager.Instance.SetProgressState(TaskbarProgressBarState.NoProgress);
                

            }
            else
                Heartbeat3++;

            if (Heartbeat6 >= 5)
            {
                Heartbeat6 = 0;
                //LIB.ThePositioner.CheckLink();//定期检查连接，没必要定期检查，在使用过程中会检查的，没有使用即使没连上没什么后果

                //SendHeartbeat();
                //SendConstUpdate();
            }
            else
                Heartbeat6++;

            if (Heartbeat50 >= 49)
            {
                Heartbeat50 = 0;
                LIB.ThePositioner.CheckLink();
            }
                
            else
                Heartbeat50++;

            Invalidate();
        }

        private void PrepSolToolStripMenuItem_Click(object sender, EventArgs e)
        {
            PrepSolution PrepSolDlg = new PrepSolution();
            if(PrepSolDlg.ShowDialog() == DialogResult.OK)
            {
                ProgStep ps = new ProgStep();
                ps.OperType = ProgStep.Operation.PrepSol;
                ps.Comps = PrepSolDlg.LConcs;
                ps.TotalVol = LIB.MixedSol.TotalVol;
                ExpProgram ep = new ExpProgram();
                ep.Steps.Add(ps);
                stepProgress.DataSource = ep.Steps;

                //LogMsgbox.Text += DateTime.Now.ToString("G") + ps.GetDesc() + "\r\n";
                //LogMsgbox.SelectionStart = this.LogMsgbox.Text.Length;
                //LogMsgbox.ScrollToCaret();
                Exp.RunProgram(ep,true);
            }
        }

        private void MainWin_FormClosing(object sender, FormClosingEventArgs e)
        {
            string Json;
            Exp.ResetComboStates();
            Json = JsonConvert.SerializeObject(LIB.CHs);
            Properties.Settings.Default.ChannelListJSON = Json;
            Json = JsonConvert.SerializeObject(LIB.LastExp);
            Properties.Settings.Default.LastExp = Json;
            Json = JsonConvert.SerializeObject(LIB.PPs);
            Properties.Settings.Default.FlushingPumpsJSON = Json;
            Json = JsonConvert.SerializeObject(LIB.ThePositioner);
            Properties.Settings.Default.PositionerJSON = Json;
            Properties.Settings.Default.TotalVol = LIB.MixedSol.TotalVol;
            Properties.Settings.Default.Save();
            LIB.RS485Driver.DetachDataReader();
            LIB.ThePositioner.DetachDataReader();
            //foreach (Diluter diluter in LIB.Diluters)
            //    diluter.ClosePort();
            //SendExitStat();
        }


        private void SingleExperiment_ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            ProgramEditor pe = new ProgramEditor();

            if (pe.ShowDialog() == DialogResult.OK)
            {
                Exp.RunProgram(LIB.LastExp, true);
                LIB.DataFilePath = Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMdd-HHmm"));
                Directory.CreateDirectory(LIB.DataFilePath);
                //SharedComponents.ExcelDataFile = new SaveAsExcel(Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMddHHmm") + ".xlsx"));
            }
            else if(!Exp.Running)
                Exp.LoadProgram(LIB.LastExp);
            stepProgress.DataSource = null;
            stepProgress.DataSource = Exp.ActiveSteps;
        }

        private void 测试用ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Tester test = new Tester();
            test.ShowDialog();
        }

        //绘制步骤列表的条目背景
        private void stepProgress_DrawItem(object sender, DrawItemEventArgs e)
        {
            if (e.Index < Exp.ActiveSteps.Count && e.Index >=0)
            {
                e.DrawBackground();
                if ((e.State & DrawItemState.Selected) != DrawItemState.Selected)
                {
                    if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.PrepSol)
                        e.Graphics.FillRectangle(new SolidBrush(Color.LightSkyBlue), e.Bounds);
                    else if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.EChem)
                        e.Graphics.FillRectangle(new SolidBrush(Color.LightPink), e.Bounds);
                    else if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.Flush)
                        e.Graphics.FillRectangle(new SolidBrush(Color.PapayaWhip), e.Bounds);
                    else if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.Transfer)
                        e.Graphics.FillRectangle(new SolidBrush(Color.LightGreen), e.Bounds);
                    else if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.Change)
                        e.Graphics.FillRectangle(new SolidBrush(Color.DarkGray), e.Bounds);
                    else if (Exp.ActiveSteps[e.Index].OperType == ProgStep.Operation.Blank)
                        e.Graphics.FillRectangle(new SolidBrush(Color.Gainsboro), e.Bounds);
                }
                e.Graphics.DrawRectangle(new Pen(Color.AntiqueWhite), e.Bounds);
                e.Graphics.DrawString((e.Index + 1).ToString("D3") + ":", e.Font, new SolidBrush(e.ForeColor), e.Bounds);
                e.Graphics.DrawString(Exp.ActiveSteps[e.Index].GetDesc(), e.Font, new SolidBrush(e.ForeColor), new Rectangle(e.Bounds.Left + 30, e.Bounds.Top, e.Bounds.Width - 20, e.Bounds.Height));
                e.DrawFocusRectangle();
            }
        }
        //TODO:太多操作在paint里面，如果绘图不更新时数据不更新！
        private void 电化学ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            EChem ec = new EChem();
            ec.Show();
        }

        private void 针筒排气ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Degas degas = new Degas();
            degas.Show();
        }

        private void 注射泵ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Manualwindow ma = new Manualwindow();
            ma.ShowDialog();
        }

        private void rS485蠕动泵ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            ManMotorsOnRS485 m485 = new ManMotorsOnRS485();
            m485.ShowDialog();
        }

        private void btnStopstep_Click(object sender, EventArgs e)
        {
            if (Exp.Running)
            {
                DialogResult result = MessageBox.Show(LIB.NamedStrings["CFMStop"], "", MessageBoxButtons.OKCancel);
                if (result == DialogResult.OK)
                {
                    Exp.ResetComboStates();//TODO:暂时无法中止已经开始的步骤。
                }
            }
            else
                Exp.ResetComboStates();//TODO:暂时无法中止已经开始的步骤。
            LogMsgbox.Focus();
        }

        private void btnRunSingleExp_Click(object sender, EventArgs e)
        {
            if(!Exp.Running)
            {
                DialogResult result = MessageBox.Show(LIB.NamedStrings["CFMRun"], "", MessageBoxButtons.OKCancel);
                if(result == DialogResult.OK)
                {
                    if (LIB.LastExp.Steps.Count > 0)
                    {
                        Exp.RunProgram(true);
                        LIB.DataFilePath = Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMdd-HHmm"));
                        Directory.CreateDirectory(LIB.DataFilePath);
                        //SharedComponents.ExcelDataFile = new SaveAsExcel(Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMddHHmm")+".xlsx"));
                    }
                    else
                        MessageBox.Show(LIB.NamedStrings["NoExpDefined"]);
                }
            }
            LogMsgbox.Focus();
        }

        private void btnResetCombop_Click(object sender, EventArgs e)
        {
            Exp.Program.ResetComboParams();
            stepProgress.DataSource = null;
            stepProgress.DataSource = Exp.ActiveSteps;
            //SharedComponents.LogMsg += "[信息]当前组合实验为" + SharedComponents.LastExp.ComboExpCount().ToString() + "个中的第" + SharedComponents.LastExp.ComboProgress().ToString() + "个。\r\n";
            LogMsgbox.Focus();
        }

        private void CombExpToolStripMenuItem_Click(object sender, EventArgs e)
        {
            //TODO:生成程序
            if (LIB.LastExp.Steps.Count > 0)
            {
                ComboExpEditor comboExpEditor = new ComboExpEditor();
                if (comboExpEditor.ShowDialog() == DialogResult.OK)
                {
                    Exp.RunComboProgram(LIB.LastExp, true);
                    LIB.DataFilePath = Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMdd-HHmm"));
                    Directory.CreateDirectory(LIB.DataFilePath);
                    //SharedComponents.ExcelDataFile = new SaveAsExcel(Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMddHHmm") + ".xlsx"));
                }
                stepProgress.DataSource = null;
                stepProgress.DataSource = Exp.ActiveSteps;
            }
            else
                MessageBox.Show(LIB.NamedStrings["NoBaseExp"]);
        }

        private void ExitToolStripMenuItem_Click(object sender, EventArgs e)
        {
            Close();
        }


        private void LoadtoolStripMenuItem_Click(object sender, EventArgs e)
        {
            string conversionerror = "";
            OpenFileDialog ofd = new OpenFileDialog();
            ofd.Filter = "txt files (*.txt)|*.txt|All files (*.*)|*.*";
            ofd.FilterIndex = 2;
            ofd.RestoreDirectory = true;
            if (ofd.ShowDialog() == DialogResult.OK)
            {
                LIB.LastExp = JsonConvert.DeserializeObject<ExpProgram>(File.ReadAllText(ofd.FileName),
                    new JsonSerializerSettings
                    {
                        Error = delegate (object jssender, Newtonsoft.Json.Serialization.ErrorEventArgs args)
                        {
                            conversionerror = args.ErrorContext.Error.Message;
                            args.ErrorContext.Handled = true;
                        }
                    });
            }
            if (conversionerror == "")
            {
                Exp.LoadProgram(LIB.LastExp);
                stepProgress.DataSource = Exp.ActiveSteps;
            }
        }

        private void btnRunComboExp_Click(object sender, EventArgs e)
        {
            if (!Exp.Running)
            {
                DialogResult result = MessageBox.Show(LIB.NamedStrings["CFMRunCombo"], "", MessageBoxButtons.OKCancel);
                if (result == DialogResult.OK)
                {
                    if (LIB.LastExp.Steps.Count > 0)
                    {
                        Exp.RunComboProgram(LIB.LastExp, true);
                        stepProgress.DataSource = null;
                        stepProgress.DataSource = Exp.ActiveSteps;
                        LIB.DataFilePath = Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMdd-HHmm"));
                        Directory.CreateDirectory(LIB.DataFilePath);
                        //SharedComponents.ExcelDataFile = new SaveAsExcel(Path.Combine(Properties.Settings.Default.DataFilePath, DateTime.Now.ToString("yyyyMMddHHmm") + ".xlsx"));
                    }
                    else
                        MessageBox.Show(LIB.NamedStrings["NoExpDefined"]);
                }
            }
            LogMsgbox.Focus();
        }

        private void btnNextCombo_Click(object sender, EventArgs e)
        {
            //SharedComponents.LastExp.NextComboIndex();
            LIB.LastExp.NextSelectComboParams();
            stepProgress.DataSource = null;
            stepProgress.DataSource = Exp.ActiveSteps;
            //SharedComponents.LastExp.NextCombParamSet();
            //SharedComponents.LogMsg += "[信息]当前组合实验为" + SharedComponents.LastExp.ComboExpCount().ToString() + "个中的第" + SharedComponents.LastExp.ComboProgress().ToString() + "个。\r\n";
            LogMsgbox.Focus();

        }

        private void btnPrevCombo_Click(object sender, EventArgs e)
        {
            LIB.LastExp.PreviousSelectComboParams();
            stepProgress.DataSource = null;
            stepProgress.DataSource = Exp.ActiveSteps;
            //SharedComponents.LogMsg += "[信息]当前组合实验为" + SharedComponents.LastExp.ComboExpCount().ToString() + "个中的第" + SharedComponents.LastExp.ComboProgress().ToString() + "个。\r\n";
            LogMsgbox.Focus();
        }

        private void btnDisplayMatrix_Click(object sender, EventArgs e)
        {
            //SharedComponents.LogMsg += Exp.Program.ListSelectParams();
            LogMsgBuffer.AddEntry(LIB.NamedStrings["Info"], Exp.Program.ListSelectParams());
            //LogMsgbox.Focus();
        }

        private void MainWin_Enter(object sender, EventArgs e)
        {
            LogMsgbox.Focus();
        }

        private void btnJumptoCombo_Click(object sender, EventArgs e)
        {
            Button btnSender = (Button)sender;
            JumptoCmbExp jtcmb = new JumptoCmbExp();
            Point ptTopLeft = new Point(0, -jtcmb.Height - 10);
            ptTopLeft = btnSender.PointToScreen(ptTopLeft);
            jtcmb.Location = ptTopLeft;
            jtcmb.MaxCmbIndex = LIB.LastExp.ConstConcExpCount;
            jtcmb.CmbIndex = LIB.LastExp.SelectComboProgress();
            if(jtcmb.ShowDialog() == DialogResult.OK)
            {
                if (btnRunComboExp.Enabled)
                {
                    LIB.LastExp.SelectComboSeekNLoad(jtcmb.CmbIndex);
                    stepProgress.DataSource = null;
                    stepProgress.DataSource = Exp.ActiveSteps;
                }
                else
                    MessageBox.Show(LIB.NamedStrings["CannotJump"]);

            }
        }

        private void stepProgress_MeasureItem(object sender, MeasureItemEventArgs e)
        {
            e.ItemHeight = (int)e.Graphics.MeasureString((e.Index + 1).ToString("D3") + ":" + Exp.ActiveSteps[e.Index].GetDesc(), stepProgress.Font, stepProgress.Width - 20).Height;
        }

        private void SendConstUpdate()
        {
            try
            {
                if (Exp.Running)
                {
                    if (Exp.ActiveSteps[Exp.CurrentStep].OperType == ProgStep.Operation.PrepSol)
                    {
                        KafkaMsg.SendMsg($"{Environment.MachineName}.Diluters", JsonConvert.SerializeObject(LIB.Diluters));
                        KafkaMsg.SendMsg($"{Environment.MachineName}.MixedSol", JsonConvert.SerializeObject(LIB.MixedSol));
                        KafkaMsg.SendMsg($"{Environment.MachineName}.WorkingElectrolyte", JsonConvert.SerializeObject(LIB.WorkingElectrolyte));
                    }
                    if (Exp.ActiveSteps[Exp.CurrentStep].OperType == ProgStep.Operation.Flush || Exp.ActiveSteps[Exp.CurrentStep].OperType == ProgStep.Operation.Transfer)
                    {
                        KafkaMsg.SendMsg($"{Environment.MachineName}.PPs", JsonConvert.SerializeObject(LIB.PPs));
                        KafkaMsg.SendMsg($"{Environment.MachineName}.MixedSol", JsonConvert.SerializeObject(LIB.MixedSol));
                        KafkaMsg.SendMsg($"{Environment.MachineName}.WorkingElectrolyte", JsonConvert.SerializeObject(LIB.WorkingElectrolyte));
                    }
                    KafkaMsg.SendMsg($"{Environment.MachineName}.ElapsedTime", JsonConvert.SerializeObject(Exp.ElapsedTime));
                    KafkaMsg.SendMsg($"{Environment.MachineName}.ElapsedStepTime", JsonConvert.SerializeObject(Exp.ElapsedStepTime));
                    KafkaMsg.SendMsg($"{Environment.MachineName}.ElapsedComboTime", JsonConvert.SerializeObject(Exp.ElapsedComboTime));
                }
                KafkaMsg.SendMsg($"{Environment.MachineName}.CurrentStep", JsonConvert.SerializeObject(Exp.CurrentStep));
                KafkaMsg.SendMsg($"{Environment.MachineName}.RemainingVol", JsonConvert.SerializeObject(RemainingVol));
                KafkaMsg.SendMsg($"{Environment.MachineName}.StepInfo", StepInfo);
                KafkaMsg.SendMsg($"{Environment.MachineName}.TimeInfo", TimeInfo);
                KafkaMsg.SendMsg($"{Environment.MachineName}.ExpRunning", JsonConvert.SerializeObject(Exp.Running));
                KafkaMsg.SendMsg($"{Environment.MachineName}.ComboExpRunning", JsonConvert.SerializeObject(Exp.ComboRunning));
            }
            catch (Exception e)
            {
                Console.WriteLine($"SendConstUpdate went wrong: {e.Message}");
            }
        }

        private void SendInitialStat()
        {
            try
            {
                KafkaMsg.SendMsg("Online", Environment.MachineName);
                KafkaMsg.SendMsg($"{Environment.MachineName}.Diluters", JsonConvert.SerializeObject(LIB.Diluters));
                KafkaMsg.SendMsg($"{Environment.MachineName}.PPs", JsonConvert.SerializeObject(LIB.PPs));
                KafkaMsg.SendMsg($"{Environment.MachineName}.CHIConnected", JsonConvert.SerializeObject(LIB.CHIConnected));
            }
            catch (Exception e)
            {
                Console.WriteLine($"SendInitialStat wrong: {e.Message}");
            }
        }

        private void SendExitStat()
        {
            try
            {
                KafkaMsg.SendMsg("Offline", Environment.MachineName);
            }
            catch (Exception e)
            {
                Console.WriteLine($"SendExitStat wrong: {e.Message}");
            }

        }

        private void SendExpStat()
        {
            try
            {
                KafkaMsg.SendMsg($"{Environment.MachineName}.ComboInfo", ComboInfo);
                KafkaMsg.SendMsg($"{Environment.MachineName}.ActiveSteps", JsonConvert.SerializeObject(Exp.ActiveSteps));
                KafkaMsg.SendMsg($"{Environment.MachineName}.ExpDuration", Exp.Duration.ToString());
            }
            catch (Exception e)
            {
                Console.WriteLine($"SendExpStat wrong: {e.Message}");
            }
        }

        private void SendHeartbeat()
        {
            try
            {
                KafkaMsg.SendMsg("Online", Environment.MachineName);
            }
            catch (Exception e)
            {
                Console.WriteLine($"SendInitialStat wrong: {e.Message}");
            }
        }

        private void stepProgress_DataSourceChanged(object sender, EventArgs e)
        {
            //SendExpStat();
        }

        private void 三轴平台ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            ManPositioner mp = new ManPositioner();
            mp.Show();
        }

        private void form1ToolStripMenuItem_Click(object sender, EventArgs e)
        {
            RS485调试 rS485 = new RS485调试();
            rS485.ShowDialog();
        }
    }
}
