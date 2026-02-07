// MotorRS485.cs
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO.Ports;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace eChemSDL
{
    public class MotorRS485 : IDisposable
    {
        private SerialPort serialPort;
        private readonly SemaphoreSlim commandLock = new SemaphoreSlim(1, 1);
        private readonly byte FWD = 0x80;
        private readonly byte RWD = 0x00;
        //在主程序里面调用这个类时，使用如下方式注册事件：
        //motorRS485.OnUnsolicitedMessageReceived += (addr, data) => { /* 处理接收到的数据 */ };
        public event Action<byte[]> OnMessageReceived;
  
        private volatile bool isReceiving = false;
        private List<byte> receiveBuffer = new List<byte>();
        private readonly Dictionary<byte, MotorState> motorStates = new Dictionary<byte, MotorState>();

        private static int GetExpectedResponseLength(byte command)
        {
            switch (command)
            {
                case 0x32: return 6; //查询电机速度
                case 0x39: return 8; //查询电机角度误差
                case 0x40: return 8;//版本信息
                case 0x47: return 38;//电机状态信息
                case 0x48: return 31;//电机设置参数
                default: return 5;
            }
        }

        public class MotorState
        {
            public bool IsRunning { get; set; }
            public DateTime LastSeen { get; set; }
            public byte[] LastResponse { get; set; }
        }
        public ReadOnlyDictionary<byte, MotorState> MotorList => new ReadOnlyDictionary<byte, MotorState>(motorStates);
        public bool MotorsOnline = false;

        // Indicates whether the serial port has been created and opened
        public bool IsReady => serialPort != null && serialPort.IsOpen;

        private void SerialPort_DataReceived(object sender, SerialDataReceivedEventArgs e)
        {
            isReceiving = true;
            int bytesToRead = serialPort.BytesToRead;
            byte[] buffer = new byte[bytesToRead];
            serialPort.Read(buffer, 0, bytesToRead);
            receiveBuffer.AddRange(buffer);
            while (receiveBuffer.Count >= 5) // minimum length of valid message
            {
                if (receiveBuffer[0] != 0xFB)
                {
                    int index = receiveBuffer.IndexOf(0xFB);
                    if (index == -1)
                    {
                        receiveBuffer.Clear();
                        break;
                    }
                    else
                    {
                        receiveBuffer.RemoveRange(0, index);
                        if (receiveBuffer.Count < 5)
                            break;
                    }
                }

                byte addr = receiveBuffer[1];
                byte cmd = receiveBuffer[2];
                int expectedLength = GetExpectedResponseLength(cmd);

                if (receiveBuffer.Count < expectedLength)
                    break; // partial message, wait for more data

                byte[] packet = receiveBuffer.GetRange(0, expectedLength).ToArray();
                receiveBuffer.RemoveRange(0, expectedLength);

                if (!motorStates.ContainsKey(addr))
                    motorStates[addr] = new MotorState();

                motorStates[addr].LastSeen = DateTime.Now;
                motorStates[addr].LastResponse = packet;
                //提取电机运行状态
                if (cmd == 0xF1)
                {
                    if (packet[3] == 0x01)
                        motorStates[addr].IsRunning = false;
                    if (packet[3] > 0x01)
                        motorStates[addr].IsRunning = true;
                }
                if (OnMessageReceived != null)
                    OnMessageReceived(packet);
            }
            if(motorStates.Count > 0)
            {
                MotorsOnline = true;
            }
            else
            {
                MotorsOnline = false;
            }
            isReceiving = false;
        }
        public void Open()
        {
            if (serialPort == null)
                throw new InvalidOperationException("Serial port not configured. Call InitializeAsync and ensure RS485 port is available.");
            serialPort.Open();
        }
        public void Close()
        {
            if (serialPort == null)
                return;
            if (serialPort.IsOpen)
                serialPort.Close();
        }
        public bool IsOpen => serialPort?.IsOpen ?? false;
        public void Dispose() => serialPort?.Dispose();

        private byte Checksum(params byte[] bytes)
        {
            int sum = 0;
            foreach (var b in bytes) sum += b;
            return (byte)sum;
        }

        private async Task<byte[]> SendCommandAsync(byte[] data)
        {
            if (serialPort == null || !serialPort.IsOpen)
                throw new InvalidOperationException("Cannot send command: serial port not initialized or not open.");

            await commandLock.WaitAsync();
            try
            {
                while (isReceiving) await Task.Delay(10);

                serialPort.DiscardInBuffer();
                serialPort.Write(data, 0, data.Length);
                await Task.Delay(25);
                return data;
            }
            finally
            {
                commandLock.Release();
            }
        }

        //position：步进电机的目标位置，单位为°，360°为一圈
        public Task<byte[]> RunRelativePositionModeAsync(byte addr, float degrees, ushort speed, bool forward, byte acceleration = 0x10)
        {
            var pos = BitConverter.GetBytes(degrees * 16384 / 360);
            var spd = BitConverter.GetBytes(speed);
            spd[1] |= (byte)(forward ? 0x00 : 0x80);

            var cmd = new byte[]
            {
            0xFA, addr, 0xF4,
            spd[1], spd[0],
            acceleration,
            pos[3], pos[2], pos[1], pos[0],
            0x00
            };
            cmd[cmd.Length - 1] = Checksum(cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], cmd[5], cmd[6], cmd[7], cmd[8], cmd[9]);
            return SendCommandAsync(cmd);
        }
        // divisions：步进电机的目标位置，单位为编码器分度数，1圈=16384分度数
        public Task<byte[]> RunRelativePositionModeAsync(byte addr, int divisions, ushort speed, bool forward, byte acceleration = 0x10)
        {
            var pos = BitConverter.GetBytes(divisions);
            var spd = BitConverter.GetBytes(speed);
            spd[1] |= (byte)(forward ? 0x00 : 0x80);

            var cmd = new byte[]
            {
            0xFA, addr, 0xF4,
            spd[1], spd[0],
            acceleration,
            pos[3], pos[2], pos[1], pos[0],
            0x00
            };
            cmd[cmd.Length - 1] = Checksum(cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], cmd[5], cmd[6], cmd[7], cmd[8], cmd[9]);
            return SendCommandAsync(cmd);
        }

        public Task<byte[]> StopRelativePositionModeAsync(byte addr, byte deceleration = 0x10)
        {
            var cmd = new byte[]
            {
                0xFA, addr, 0xF4, 0x00, 0x00, deceleration,
                0x00, 0x00, 0x00, 0x00,
                Checksum(0xFA, addr, 0xF4, 0x00, 0x00, deceleration, 0x00, 0x00, 0x00, 0x00)
            };
            return SendCommandAsync(cmd);
        }

        public Task<byte[]> GetVersionAsync(byte addr)
        {
            var cmd = new byte[] { 0xFA, addr, 0x40, Checksum(0xFA, addr, 0x40) };
            return SendCommandAsync(cmd);
        }

        public Task<byte[]> ReadAllSettingsAsync(byte addr)
        {
            var cmd = new byte[] { 0xFA, addr, 0x47, Checksum(0xFA, addr, 0x47) };
            return SendCommandAsync(cmd);
        }

        //查找电机所有状态参数
        public Task<byte[]> ReadAllStatusAsync(byte addr)
        {
            var cmd = new byte[] { 0xFA, addr, 0x48, Checksum(0xFA, addr, 0x48) };
            return SendCommandAsync(cmd);
        }
        //查询电机运行状态
        public Task<byte[]> GetRunStatusAsync(byte addr)
        {
            var cmd = new byte[] { 0xFA, addr, 0xF1, Checksum(0xFA, addr, 0xF1) };
            return SendCommandAsync(cmd);
        }

        public Task<byte[]> RunSpeedModeAsync(byte addr, ushort speed = 100, bool forward = true, byte acceleration = 0x10)
        {
            var spd = BitConverter.GetBytes(speed);
            spd[1] |= forward ? FWD : RWD;
            byte chk = Checksum(0xFA, addr, 0xF6, spd[1], spd[0], acceleration);
            return SendCommandAsync(new byte[] { 0xFA, addr, 0xF6, spd[1], spd[0], acceleration, chk });
        }

        public Task<byte[]> StopSpeedModeAsync(byte addr, byte deceleration = 0x10) => SendCommandAsync(new byte[]
        {
            0xFA, addr, 0xF6, 0x00, 0x00, deceleration, Checksum(0xFA, addr, 0xF6, 0x00, 0x00, deceleration)
        });

        public async Task DiscoverMotorsAsync()
        {
            for (byte addr = 1; addr < 32; addr++)//我想不会多于32个从机
            {
                await GetRunStatusAsync(addr);
                await Task.Delay(10);
            }
        }

        public async Task InitializeAsync()
        {
            // Ensure we always use the currently configured RS485 port; recreate serialPort if port changed
            string portName = Properties.Settings.Default.RS485Port;

            if (string.IsNullOrEmpty(portName) || !LIB.AvailablePorts.Contains(portName))
            {
                // configured port not available; leave serialPort as null and return
                return;
            }

            bool needCreate = false;
            if (serialPort == null)
            {
                needCreate = true;
            }
            else if (!string.Equals(serialPort.PortName, portName, StringComparison.OrdinalIgnoreCase))
            {
                // different port configured; dispose existing and recreate
                try
                {
                    if (serialPort.IsOpen)
                        serialPort.Close();
                }
                catch { }
                try { serialPort.Dispose(); } catch { }
                serialPort = null;
                needCreate = true;
            }

            if (needCreate)
            {
                serialPort = new SerialPort
                {
                    PortName = portName,
                    BaudRate = 38400, //RS485电机的波特率
                    DataBits = 8,
                    StopBits = StopBits.Two,
                    Parity = Parity.None,
                    ReadTimeout = 500,
                    WriteTimeout = 500
                };
            }

            if (serialPort != null)
            {
                try
                {
                    if (!serialPort.IsOpen)
                        serialPort.Open();

                    // ensure event only attached once
                    serialPort.DataReceived -= SerialPort_DataReceived;
                    serialPort.DataReceived += SerialPort_DataReceived;

                    // clear previous state and discover motors
                    motorStates.Clear();
                    MotorsOnline = false;

                    await DiscoverMotorsAsync();

                    // give some time for devices to respond and DataReceived to populate motorStates
                    await Task.Delay(200);

                    // attach existing diluters if any listeners rely on driver
                    foreach (var kvp in motorStates)
                    {
                        byte addr = kvp.Key;
                        var state = kvp.Value;
                        if (state.IsRunning)
                        {
                            Console.WriteLine($"Motor {addr} is running. Last response: {BitConverter.ToString(state.LastResponse)}");
                        }
                        else
                        {
                            Console.WriteLine($"Motor {addr} is not running. Last response: {BitConverter.ToString(state.LastResponse)}");
                        }
                    }
                }
                catch (UnauthorizedAccessException)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Warning") ? LIB.NamedStrings["Warning"] : "Warning", LIB.NamedStrings.ContainsKey("Flush") ? LIB.NamedStrings["Flush"] + LIB.NamedStrings["PortOccupied"] : "Port occupied");
                }
                catch (Exception ex)
                {
                    LogMsgBuffer.AddEntry(LIB.NamedStrings.ContainsKey("Warning") ? LIB.NamedStrings["Warning"] : "Warning", "RS485 init error: " + ex.Message);
                }
            }

        }

        public string[] GetAddressStr()
        {
            List<string> addrList = new List<string>();
            foreach(var kvp in motorStates)
            {
                byte addr = kvp.Key;
                addrList.Add(addr.ToString("D2"));
            }
            return addrList.ToArray();
        }

        public byte[] GetAddressBytes()
        {
            List<byte> addrList = new List<byte>();
            foreach (var kvp in motorStates)
            {
                byte addr = kvp.Key;
                addrList.Add(addr);
            }
            return addrList.ToArray();
        }

        public void DetachDataReader()
        {
            if (serialPort != null)
            {
                try
                {
                    serialPort.DataReceived -= SerialPort_DataReceived;
                }
                catch { }
                try
                {
                    if (serialPort.IsOpen)
                        serialPort.Close();
                }
                catch { }
                try { serialPort.Dispose(); } catch { }
                serialPort = null;
            }
        }

        public Task<byte[]> RunbySpeed(byte addr, ushort speed, bool dir, byte acc) => RunSpeedModeAsync(addr, speed, dir, acc);
        public Task<byte[]> Run(byte addr) => RunSpeedModeAsync(addr);
        public Task<byte[]> Run(byte addr, ushort speed, bool dir) => RunSpeedModeAsync(addr, speed, dir); // 默认速度100
        public Task<byte[]> CWRun(byte addr, ushort speed) => RunSpeedModeAsync(addr, speed, true); // 默认速度100，顺时针运行
        public Task<byte[]> CCWRun(byte addr, ushort speed) => RunSpeedModeAsync(addr, speed, false); // 默认速度100，逆时针运行
        public Task<byte[]> Stop(byte addr) => StopSpeedModeAsync(addr);//注意这个只能停止速度模式下的运行
        public Task<byte[]> Turn(byte addr, int degrees, ushort speed, bool forward, byte acceleration = 0x10) => RunRelativePositionModeAsync(addr, degrees, speed, forward, acceleration);
        public Task<byte[]> TurnTo(byte addr, int divisions) => RunRelativePositionModeAsync(addr,divisions, 100, true, 0x10); // 默认速度100，顺时针运行到指定编码值
        public Task<byte[]> TurnTo(byte addr, float degrees) => RunRelativePositionModeAsync(addr, degrees, 100, true, 0x10); // 默认速度100，顺时针运行到指定角度
        public Task<byte[]> Break(byte addr) => StopRelativePositionModeAsync(addr);//注意这个只能停止相对位置模式下的运行
        public Task Initialize() => InitializeAsync();
        public Task SendCommand(byte[] cmd) => SendCommandAsync(cmd);
    }
}
