using System;
using System.Collections.Generic;
using System.Windows.Forms;

namespace eChemSDL
{
    public partial class EnterSelected : Form
    {
        public EnterSelected()
        {
            InitializeComponent();
            List<int> selectedlist = new List<int>();
            for (int i = 1; i <= LIB.LastExp.ConstConcExpCount; i++)
            {
                //保存在程序里的是Skiplist，显示给用户的是反过来的Selectlist
                if (!LIB.LastExp.UserSkip(i))
                    selectedlist.Add(i);
            }
            txtSelectedIndexes.Text = ListtoString(selectedlist);
        }

        private void btnOK_Click(object sender, EventArgs e)
        {
            List<int> skiplist = new List<int>();
            List<int> selectedlist = new List<int>();
            selectedlist = StringtoList(txtSelectedIndexes.Text);
            for (int i = 1; i <= LIB.LastExp.ConstConcExpCount; i++)
            {
                //保存在程序里的是Skiplist，显示给用户的是反过来的Selectlist
                if (!selectedlist.Contains(i))
                    skiplist.Add(i);
            }
            LIB.LastExp.UpdateUserSkipList(skiplist);
        }

        private string ListtoString(List<int> list)
        {
            string str="";
            int start, end;  // track start and end
            if (list.Count > 0)
            {
                end = start = list[0];
                for (int i = 1; i < list.Count; i++)
                {
                    // as long as entries are consecutive, move end forward
                    if (list[i] == (list[i - 1] + 1))
                    {
                        end = list[i];
                    }
                    else
                    {
                        // when no longer consecutive, add group to result
                        // depending on whether start=end (single item) or not
                        if (start == end)
                            str += start + ",";
                        else
                            str += start + "-" + end + ",";

                        start = end = list[i];
                    }
                }
                // handle the final group
                if (start == end)
                    str += start;
                else
                    str += start + "-" + end;
            }
            return str;
        }

        private List<int> StringtoList(string str)
        {
            List<int> list = new List<int>();
            string[] numbers = str.Split(',');
            if(numbers.Length>0)
            {
                for (int i = 0; i < numbers.Length; i++)
                {
                    string tmpDigit = numbers[i];
                    if (tmpDigit.Contains("-"))
                    {
                        int start = int.Parse(tmpDigit.Split('-')[0].ToString());
                        int end = int.Parse(tmpDigit.Split('-')[1]);

                        for (int j = start; j <= end; j++)
                        {
                            if (!list.Contains(j))
                                list.Add(j);
                        }
                    }
                    else if(tmpDigit.Length>0)
                    {
                        list.Add(int.Parse(tmpDigit));
                    }
                }
            }
            return list;
        }

    }
}
