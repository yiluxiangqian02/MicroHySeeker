using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;
using System.Windows.Forms.DataVisualization.Charting;

namespace eChemSDL
{
    public partial class EChem : Form
    {
        [DllImport(".\\libec.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern int CHI_getTechnique();
        public float[] a = new float[1000000];
        public float[] b = new float[1000000];

        public BindingList<PointF> data = new BindingList<PointF>();

        private BindingSource bs = new BindingSource();

        public EChem()
        {
            InitializeComponent();

        }

        private void EChem_Load(object sender, EventArgs e)
        {
            bs.DataSource = data;
            dataGridView1.AutoGenerateColumns = false;
            dataGridView1.DataSource = data;
            dataGridView1.Columns[0].ReadOnly = false;
            dataGridView1.Columns[1].ReadOnly = false;
            dataGridView1.Columns[0].DataPropertyName = "X";
            dataGridView1.Columns[1].DataPropertyName = "Y";

            chart1.Series.First().ChartType = SeriesChartType.FastLine;
            chart1.DataSource = data;
            chart1.Series.First().XValueMember = "X";
            chart1.Series.First().YValueMembers = "Y";
        }

        private void button1_Click(object sender, EventArgs e)
        {
            string tech;
            string model;
            //char[] buffer = new char[256];

            //model = new string(buffer);
            tech = "";
            //tech += model;
            tech += "\r\ntechniques:\r\n";
            for(int i = 0; i< 44; i++)
            {
                    tech += i.ToString() + ":"+ CHI_getTechnique().ToString() + "\r\n";

            }
            MessageBox.Show(tech);

        }

        private void Runexp_DoWork(object sender, DoWorkEventArgs e)
        {
            BackgroundWorker worker = sender as BackgroundWorker;
            Random rnd = new Random();

            for (int i = 1; i < 1000000; i++)
            {
                if (worker.CancellationPending == true)
                {
                    e.Cancel = true;
                    break;
                }
                else
                {
                    // Perform a time consuming operation and report progress.
                    //                    System.Threading.Thread.Sleep(500);
                    a[i] = i;
                    b[i] = (float)(rnd.Next(5) + rnd.NextDouble());
                    //worker.ReportProgress(i * 10);
                }
            }
        }

        private void button2_Click(object sender, EventArgs e)
        {

        }

        private void Runexp_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            progressBar1.Value = e.ProgressPercentage;
        }

        private void button3_Click(object sender, EventArgs e)
        {
            if (Runexp.IsBusy != true)
            {
                // Start the asynchronous operation.
                Runexp.RunWorkerAsync();
            }

            Random rnd = new Random();
        }

        private void Runexp_RunWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            data.Clear();
            //chart1.Series.First().Points.Clear();
            for (int i = 0; i < 1000; i++)
            {
                //chart1.Series.FirstOrDefault().Points.AddXY(a[i], b[i]);
                data.Add(new PointF(a[i],b[i]));
            }
            chart1.DataBind();
            
            
        }
    }
}
