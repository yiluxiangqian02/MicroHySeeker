using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace eChemSDL
{
    static class ECTechs
    {
        //技术代号
        public const int M_CV = 0;
        public const int M_LSV = 1;
        public const int M_SCV = 2;
        public const int M_TAFEL = 3;
        public const int M_CA = 4;
        public const int M_CC = 5;
        public const int M_DPV = 6;
        public const int M_NPV = 7;
        public const int M_SWV = 8;
        public const int M_ACV = 9;
        public const int M_SHACV = 10;
        public const int M_IT = 11;
        public const int M_BE = 12;
        public const int M_HMV = 13;
        public const int M_IMP = 14;
        public const int M_CP = 15;
        public const int M_PSA = 16;
        public const int M_IMPT = 17;
        public const int M_DPA = 18;
        public const int M_TPA = 19;
        public const int M_DDPA = 20;
        public const int M_CPCR = 21;
        public const int M_DNPV = 22;
        public const int M_SECM = 23;
        public const int M_PAC = 24;
        public const int M_PSC = 25;
        public const int M_OCPT = 26;
        public const int M_SSF = 27;
        public const int M_IMPE = 28;
        public const int M_STEP = 29;
        public const int M_QCM = 30;
        public const int M_SSTEP = 31;
        public const int M_CPCS = 32;
        public const int M_IPAD = 33;
        public const int M_SPC = 34;
        public const int M_SWG = 35;
        public const int M_SONIC = 36;
        public const int M_ECN = 37;
        public const int M_SMPL = 38;
        public const int M_SISECM = 39;
        public const int M_LVDT = 40;
        public const int M_FTACV = 41;
        public const int M_ZCCC = 42;
        public const int M_ICHRG = 43;
        public const int M_ACTB = 44;

        public static Dictionary<string, int> Map = new Dictionary<string, int>
        {
            {"CV", M_CV},
            {"LSV", M_LSV},
            {"i-t", M_IT}
        };
        static ECTechs()
        {
        }
    }
}
