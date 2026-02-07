using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using OfficeOpenXml;

namespace HTPSolution
{
    public class SaveAsExcel
    {
        private ExcelPackage DataExcel = new ExcelPackage();
        private ExcelWorksheet DataSheet;
        private string FilePath;
        private string SheetName;
        private Point Pointer;

        public SaveAsExcel(string filepath)
        {
            FilePath = filepath;
            DataExcel = new ExcelPackage();
            DataSheet = DataExcel.Workbook.Worksheets.Add("原始数据");
            //ws.Cells.LoadFromText(datastring);
            DataExcel.SaveAs(new FileInfo(filepath));
            Pointer = new Point(1, 1);
        }

        public void Save()
        {
            DataExcel.Save();
        }

        public void AppendData(string datastring)
        {
            //DataSheet.
            DataExcel = new ExcelPackage(new FileInfo(FilePath));
            DataSheet = DataExcel.Workbook.Worksheets["原始数据"];
            DataSheet.Cells[Pointer.Y, Pointer.X].LoadFromText(datastring);//Cells[行，列]为了避免误解，把Y（行）放前面。
            DataSheet.Column(Pointer.X).Width = 30;
            DataSheet.Column(Pointer.X + 1).Width = 30;
            Pointer.Y += datastring.Split('\n').Length;
            if (Pointer.Y < 15)
                Pointer.Y = 15;//统一数据起始行
            DataExcel.Save();
        }

        public void AppendData(List<PointF> pointF)
        {
            DataExcel = new ExcelPackage(new FileInfo(FilePath));
            DataSheet = DataExcel.Workbook.Worksheets["原始数据"];
            DataSheet.Cells[Pointer.Y, Pointer.X].LoadFromCollection(pointF);
            DataSheet.Column(Pointer.X).Width = 15;
            DataSheet.Column(Pointer.X + 1).Width = 15;
            Pointer.Y += pointF.Count();
            DataExcel.Save();
        }

        public void AppendData(PointF pointF)
        {
            DataExcel = new ExcelPackage(new FileInfo(FilePath));
            DataSheet = DataExcel.Workbook.Worksheets["原始数据"];
            DataSheet.Cells[Pointer.Y, Pointer.X].Value = pointF.X;
            DataSheet.Cells[Pointer.Y, Pointer.X + 1].Value = pointF.Y;
            DataSheet.Column(Pointer.X).Width = 15;
            DataSheet.Column(Pointer.X + 1).Width = 15;
            Pointer.Y++;
            DataExcel.Save();
        }

        public void NextDataColumn()
        {
            Pointer.X += 2;
            Pointer.Y = 1;
        }
    }
}
