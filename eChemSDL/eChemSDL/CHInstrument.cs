using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;

namespace eChemSDL
{
    public class CHInstrument
    {
        //导入库
        //笔记：在c#里面byte和char一般不一样，导入dll时需要将char改为byte
        //在运行时目录下除了libec.dll的库还需要有Qt和MSCRT的库
        //要测试仪器是否连接，可运行一个假的实验，如果没有连接会返回错误信息，包含link failed字符，读取实验数据不能触发错误
        //而且只有运行实验的函数才有返回值判断是否运行成功。
        //6E类仪器不支持LSV可在程序里用CV代替
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern byte CHI_hasTechnique(int x);
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void CHI_setTechnique(int x);
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void CHI_setParameter(byte[] id, float newValue);
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern bool CHI_runExperiment();
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern byte CHI_experimentIsRunning();
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void CHI_showErrorStatus();
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void CHI_getExperimentData(float[] x, float[] y, int n);
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern void CHI_getErrorStatus(byte[] buffer, int length);
        [DllImport("libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern float CHI_getParameter(byte[] id);

        public float Sensitivity = 0.000001F;//灵敏读v/a

        public float[] x;
        public float[] y;
        public int n = 65536;//TODO:仪器缓存大小？
        public int duration;
        public DateTime StartTime;
        public double StepSeconds;
        public bool CHIRunning;
        public string Description;
        public string Technique;

        public List<int> Techniques = new List<int>();

        private BackgroundWorker ReadData;

        public CHInstrument()
        {
            CHIInitialize();
        }

        public void CHIInitialize()
        {
            byte[] errormsg = new byte[100];

            ReadData = new BackgroundWorker();
            ReadData.WorkerReportsProgress = true;
            ReadData.WorkerSupportsCancellation = true;
            ReadData.DoWork += ReadData_DoWork;
            ReadData.ProgressChanged += ReadData_ProgressChanged;
            ReadData.RunWorkerCompleted += ReadData_RunWorkerCompleted;

            CHIRunning = false;
            x = new float[n];
            y = new float[n];

            LIB.CHIConnected = false;

            try
            {
                for (int i = 0; i <= 44; i++)
                {
                    if (CHI_hasTechnique(i) == 1)
                        Techniques.Add(i);//这个列表，暂时没有什么用？
                }
                CHI_setParameter(Encoding.ASCII.GetBytes("m_iSens"), Sensitivity);
                CHI_setParameter(Encoding.ASCII.GetBytes("m_ei"), 0);
                CHI_setParameter(Encoding.ASCII.GetBytes("m_eh"), 0);
                CHI_setParameter(Encoding.ASCII.GetBytes("m_el"), 0);
                CHI_setParameter(Encoding.ASCII.GetBytes("m_ef"), 0);
                CHI_setParameter(Encoding.ASCII.GetBytes("m_inpcl"), 1);
                CHI_setTechnique(ECTechs.M_CV);//CV是所有型号都支持的
                //测试是否连接，只能通过运行一个假实验，并查看错误码来判断
                //但是它会尝试打开一个串口，然后不关闭它！尤其是没有连接电化学工作站的时候。
                //找不到关闭串口的方法，只能让它在其他访问串口的操作后再进行这个操作。
                //因为这个问题，导致在手动调整蠕动泵/注射泵时需要操作串口时会拒绝访问。
                //所以手动模式前必须在系统设置好串口。
                LIB.CHIConnected = true;
                if (!CHI_runExperiment())
                {
                    CHI_getErrorStatus(errormsg, 100);
                    if (Encoding.UTF8.GetString(errormsg, 0, 100).Contains("Link failed"))
                    {
                        LIB.CHIConnected = false;
                        string warning = LIB.NamedStrings["ECStation"] + " " + LIB.NamedStrings["NoConnection"];
                        LogMsgBuffer.AddEntry(LIB.NamedStrings["Warning"], warning);
                    }
                }
            }
            catch (DllNotFoundException ex)
            {
                LIB.CHIConnected = false;
                string warning = "libec.dll " + (LIB.NamedStrings.ContainsKey("NotFound") ? LIB.NamedStrings["NotFound"] : "未找到") + 
                                ", " + (LIB.NamedStrings.ContainsKey("SimMode") ? LIB.NamedStrings["SimMode"] : "将使用模拟模式");
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Warning") ? LIB.NamedStrings["Warning"] : "警告", warning);
            }
            catch (Exception ex)
            {
                LIB.CHIConnected = false;
                string warning = (LIB.NamedStrings.ContainsKey("ECInitFailed") ? LIB.NamedStrings["ECInitFailed"] : "电化学工作站初始化失败") + 
                                ": " + ex.Message;
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "错误", warning);
            }
        }

        private void ReadData_DoWork(object sender, DoWorkEventArgs e)
        {
            CHIRunning = true;
            LIB.VAPoints.Clear();
            for (int i = 0; i < n; i++)//每次实验前初始化为0
            {
                x[i] = 0;
                y[i] = 0;
            }
            BackgroundWorker worker = sender as BackgroundWorker;
            if (LIB.CHIConnected)
            {
                try
                {
                    if (!CHI_runExperiment())//启动实验
                    {
                        CHI_showErrorStatus();
                    }
                    int lastpoint = 0;
                    while (CHI_experimentIsRunning() == 1)
                    {
                        if (worker.CancellationPending == true)
                        {
                            e.Cancel = true;
                            break;
                        }
                        CHI_getExperimentData(x, y, n);
                        List<PointF> readdata = new List<PointF>();
                        int i = lastpoint;//从上次的点开始复制数据
                        for (; i < n && y[i] != 0; i++)
                        {
                            readdata.Add(new PointF(x[i], y[i]));
                        }
                        lastpoint = i;
                        lock (LIB.VAPoints)
                            LIB.VAPoints.AddRange(readdata);
                        System.Threading.Thread.Sleep(50);
                    }
                }
                catch (Exception ex)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "错误",
                                         (LIB.NamedStrings.ContainsKey("ECExpError") ? LIB.NamedStrings["ECExpError"] : "电化学实验运行错误") + 
                                         ": " + ex.Message);
                }
            }
            else
            {
                //随机数模拟
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Info") ? LIB.NamedStrings["Info"] : "信息",
                                     LIB.NamedStrings.ContainsKey("SimExp") ? LIB.NamedStrings["SimExp"] : "模拟实验");
                StartTime = DateTime.Now;
                Random random = new Random();
                PointF simdata = new PointF();
                int i = 0;
                while ((DateTime.Now - StartTime).TotalSeconds < StepSeconds)
                {
                    if (worker.CancellationPending == true)
                    {
                        e.Cancel = true;
                        break;
                    }
                    simdata = new PointF(i, (float)random.NextDouble());
                    lock (LIB.VAPoints)
                        LIB.VAPoints.Add(simdata);
                    i++;
                    System.Threading.Thread.Sleep(50);
                }
            }
            worker.ReportProgress(100);
        }

        private void ReadData_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {

        }

        private void ReadData_RunWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            CHIRunning = false;
            string datastring;
            datastring = Description + "\r\n";
            datastring += (LIB.NamedStrings.ContainsKey("Electrolyte") ? LIB.NamedStrings["Electrolyte"] : "电解液") + " " + 
                         (LIB.NamedStrings.ContainsKey("Info") ? LIB.NamedStrings["Info"] : "信息") + ":\r\n";//插入文件头
            
            if (LIB.MixedSol != null && LIB.MixedSol.SoluteList != null)
            {
                foreach (SingleSolution ss in LIB.MixedSol.SoluteList)
                    datastring += ss.Solute + "," + ss.LowConc.ToString() + "\r\n";
            }

            lock(LIB.VAPoints)
            {
                for (int i = 0; i < LIB.VAPoints.Count; i++)
                {
                    if (LIB.VAPoints[i].X != 0F && LIB.VAPoints[i].Y != 0F)
                        datastring += LIB.VAPoints[i].X.ToString() + "," + LIB.VAPoints[i].Y.ToString() + "\r\n";
                }
            }

            try
            {
                if (!string.IsNullOrEmpty(LIB.DataFilePath))
                {
                    if (!Directory.Exists(LIB.DataFilePath))
                        Directory.CreateDirectory(LIB.DataFilePath);
                    
                    string filename = LIB.DataFilePath + "\\[" + LIB.ExpIDString + "] " + Technique + DateTime.Now.ToString(" HHmmss") + ".csv";
                    File.WriteAllText(filename, datastring, Encoding.UTF8);
                    LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Info") ? LIB.NamedStrings["Info"] : "信息",
                                         LIB.NamedStrings.ContainsKey("ECDataSaved") ? LIB.NamedStrings["ECDataSaved"] : "电化学测试数据已自动保存");
                }
            }
            catch (Exception ex)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "错误",
                                     (LIB.NamedStrings.ContainsKey("SaveDataError") ? LIB.NamedStrings["SaveDataError"] : "保存数据失败") + 
                                     ": " + ex.Message);
            }
        }


        public void SetExperiment(ProgStep ps)
        {
            if (!LIB.CHIConnected)
            {
                StepSeconds = ps.Duration;
                Description = LIB.ExpIDString + "\r\n";
                Description += ps.GetDesc();
                Technique = ps.CHITechnique;
                return;
            }

            try
            {
                StepSeconds = ps.Duration;
                Description = LIB.ExpIDString + "\r\n";
                Description += ps.GetDesc();
                Technique = ps.CHITechnique;
                if (ps.CHITechnique.Equals("CV"))
                {
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_ei"), ps.E0);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_eh"), ps.EH);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_el"), ps.EL);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_ef"), ps.EF);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_vv"), ps.ScanRate);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_qt"), ps.QuietTime);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_inpcl"), ps.SegNum);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_pn"), ps.ScanDir);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_inpsi"), ps.SamplingInterval);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_bAutoSens"), ps.AutoSensibility);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_iSens"), ps.Sensitivity);

                    CHI_setTechnique(ECTechs.M_CV);
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("E0") ? LIB.NamedStrings["E0"] : "E0") + "," + ps.E0.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("EH") ? LIB.NamedStrings["EH"] : "EH") + "," + ps.EH.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("EL") ? LIB.NamedStrings["EL"] : "EL") + "," + ps.EL.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("EF") ? LIB.NamedStrings["EF"] : "EF") + "," + ps.EF.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("ScanRate") ? LIB.NamedStrings["ScanRate"] : "扫速") + "," + ps.ScanRate.ToString();
                }
                if (ps.CHITechnique.Equals("LSV"))
                {
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_ei"), ps.E0);
                    if (ps.EF > ps.E0)
                    {
                        CHI_setParameter(Encoding.ASCII.GetBytes("m_eh"), ps.EF);
                        CHI_setParameter(Encoding.ASCII.GetBytes("m_pn"), 1);
                    }
                    else
                    {
                        CHI_setParameter(Encoding.ASCII.GetBytes("m_el"), ps.EF);
                        CHI_setParameter(Encoding.ASCII.GetBytes("m_pn"), 0);

                    }

                    CHI_setParameter(Encoding.ASCII.GetBytes("m_vv"), ps.ScanRate);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_qt"), ps.QuietTime);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_inpcl"), 1);//只扫一段
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_inpsi"), ps.SamplingInterval);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_bAutoSens"), ps.AutoSensibility);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_iSens"), ps.Sensitivity);
                    CHI_setTechnique(ECTechs.M_CV);

                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("E0") ? LIB.NamedStrings["E0"] : "E0") + "," + ps.E0.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("EF") ? LIB.NamedStrings["EF"] : "EF") + "," + ps.EF.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("ScanRate") ? LIB.NamedStrings["ScanRate"] : "扫速") + "," + ps.ScanRate.ToString();

                }
                if (ps.CHITechnique.Equals("i-t"))
                {
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_ei"), ps.E0);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_qt"), ps.QuietTime);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_st"), ps.RunTime);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_inpsi"), ps.SamplingInterval);
                    CHI_setParameter(Encoding.ASCII.GetBytes("m_iSens"), ps.Sensitivity);

                    CHI_setTechnique(ECTechs.M_IT);
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("E0") ? LIB.NamedStrings["E0"] : "E0") + "," + ps.E0.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("QuietTime") ? LIB.NamedStrings["QuietTime"] : "静止时间") + "," + ps.QuietTime.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("RunTime") ? LIB.NamedStrings["RunTime"] : "运行时间") + "," + ps.RunTime.ToString();
                    Description += "\r\n" + (LIB.NamedStrings.ContainsKey("SamplingInterval") ? LIB.NamedStrings["SamplingInterval"] : "采样间隔") + "," + ps.SamplingInterval;
                }
            }
            catch (Exception ex)
            {
                LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Error") ? LIB.NamedStrings["Error"] : "错误",
                                     (LIB.NamedStrings.ContainsKey("SetExpError") ? LIB.NamedStrings["SetExpError"] : "设置实验参数失败") + 
                                     ": " + ex.Message);
            }
        }

        public void RunExperiment(ProgStep ps)
        {
            SetExperiment(ps);
            RunExperiment();
        }

        public void CancelSimulation()
        {
            if (ReadData != null)
                ReadData.CancelAsync();
        }

        public void RunExperiment()
        {
            if (ReadData != null && ReadData.IsBusy != true)
                ReadData.RunWorkerAsync();
        }
    }
}
