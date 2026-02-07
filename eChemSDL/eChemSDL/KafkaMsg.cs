using Confluent.Kafka;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Threading;

namespace KafkaMessage
{
    //Test temp
    public static class KafkaMsg
    {
        public static BackgroundWorker ReadThread = new BackgroundWorker();
        public static List<string> Topics = new List<string>();
        public static CancellationToken CnclToken;
        public static bool ReadOne;
        public static Action<ConsumeResult<string,string>> ReaderCallback;
        public static IProducer<string, string> Producer;
        public static IConsumer<string, string> Consumer;
        //static KafkaMsg()
        //{
        //    ReadThread.DoWork += ReadMsg;
        //    ReadThread.WorkerSupportsCancellation = true;
        //}

        private static void ReadMsg(object sender, DoWorkEventArgs e)
        {
            BackgroundWorker worker = sender as BackgroundWorker;
            if (worker.CancellationPending == true)
            {
                e.Cancel = true;
            }
            else
            {
                Loop_ReadMsg();
                e.Cancel = true;
            }
        }

        public static void SendMsg(string key, string value, Action<DeliveryReport<string,string>> callback)
        {
            string topicName = "7sj16z76-info";
            var config = new ProducerConfig
            {
                BootstrapServers = "omnibus-01.srvs.cloudkafka.com:9094,omnibus-02.srvs.cloudkafka.com:9094,omnibus-03.srvs.cloudkafka.com:9094",
                SecurityProtocol = SecurityProtocol.SaslSsl,
                SaslMechanism = SaslMechanism.ScramSha256,
                SaslUsername = "7sj16z76",
                SaslPassword = "cFpEQkwz7ffL2nyxQGIKOZMeG5T9HY_f"
            };
            try
            {
                if(Producer == null)
                    Producer = new ProducerBuilder<string, string>(config).Build();
                Producer.Produce(topicName, new Message<string, string> { Key = key, Value = value }, callback);
            }
            catch (Exception e)
            {
                Console.WriteLine($"something wrong: {e.Message}");
            }
        }

        public static void SendMsg(string key, string value)
        {
            string topicName = "7sj16z76-info";
            var config = new ProducerConfig
            {
                BootstrapServers = "omnibus-01.srvs.cloudkafka.com:9094,omnibus-02.srvs.cloudkafka.com:9094,omnibus-03.srvs.cloudkafka.com:9094",
                SecurityProtocol = SecurityProtocol.SaslSsl,
                SaslMechanism = SaslMechanism.ScramSha256,
                SaslUsername = "7sj16z76",
                SaslPassword = "cFpEQkwz7ffL2nyxQGIKOZMeG5T9HY_f"
            };
            try
            {
                if(Producer == null)
                    Producer = new ProducerBuilder<string, string>(config).Build();
                Producer.Produce(topicName, new Message<string, string> { Key = key, Value = value }, HandleFeedback);
            }
            catch (Exception e)
            {
                Console.WriteLine($"something wrong: {e.Message}");
            }
        }

        private static void HandleFeedback(DeliveryReport<string, string> obj)
        {
            if (obj.Error.Code == ErrorCode.NoError)
            {
                Console.WriteLine("Success");
                Console.WriteLine("Topic=" + obj.TopicPartitionOffset.Topic);
                Console.WriteLine("Particion=" + obj.TopicPartitionOffset.Partition.ToString());
                Console.WriteLine("Offset=" + obj.TopicPartitionOffset.Offset.ToString());
                Console.WriteLine(JsonConvert.SerializeObject(obj.Message));
            }
            //if (obj.Error == Success)
            else
                Console.WriteLine(obj.Error.ToString());
            //else
            //    MessageBox.Show(obj.Message.ToString());
        }

        public static void StartRead(List<string> topics, CancellationToken cancellationToken, bool readone, Action<ConsumeResult<string,string>> callback)
        {
            Topics = topics;
            ReadOne = readone;
            CnclToken = cancellationToken;
            ReaderCallback = callback;
            ReadThread.DoWork += ReadMsg;
            ReadThread.WorkerSupportsCancellation = true;

            if (!ReadThread.IsBusy)
                ReadThread.RunWorkerAsync();
        }

        private static void Loop_ReadMsg()
        {
            //官网的例程
            //https://github.com/confluentinc/confluent-kafka-dotnet/blob/master/examples/Consumer/Program.cs

            var config = new ConsumerConfig
            {
                BootstrapServers = "omnibus-01.srvs.cloudkafka.com:9094,omnibus-02.srvs.cloudkafka.com:9094,omnibus-03.srvs.cloudkafka.com:9094",
                GroupId = "HTPMonitor",
                SecurityProtocol = SecurityProtocol.SaslSsl,
                SaslMechanism = SaslMechanism.ScramSha256,
                SaslUsername = "7sj16z76",
                SaslPassword = "cFpEQkwz7ffL2nyxQGIKOZMeG5T9HY_f",

                EnableAutoCommit = false,
                //StatisticsIntervalMs = 5000,
                SessionTimeoutMs = 30000,
                AutoOffsetReset = AutoOffsetReset.Latest,
                EnablePartitionEof = true
            };

            const int commitPeriod = 5;

            // Note: If a key or value deserializer is not set (as is the case below), the 
            // deserializer corresponding to the appropriate type from Confluent.Kafka.Deserializers
            // will be used automatically (where available). The default deserializer for string
            // is UTF8. The default deserializer for Ignore returns null for all input data
            // (including non-null data).
            using (var consumer = new ConsumerBuilder<string, string>(config)
                // Note: All handlers are called on the main .Consume thread.
                .SetErrorHandler((_, e) => Console.WriteLine($"Error: {e.Reason}"))
                //.SetStatisticsHandler((_, json) => Console.WriteLine($"Statistics: {json}"))
                .SetPartitionsAssignedHandler((c, partitions) =>
                {
                    Console.WriteLine($"Assigned partitions: [{string.Join(", ", partitions)}]");
                    // possibly manually specify start offsets or override the partition assignment provided by
                    // the consumer group by returning a list of topic/partition/offsets to assign to, e.g.:
                    // 
                    // return partitions.Select(tp => new TopicPartitionOffset(tp, externalOffsets[tp]));
                })
                .SetPartitionsRevokedHandler((c, partitions) =>
                {
                    Console.WriteLine($"Revoking assignment: [{string.Join(", ", partitions)}]");
                })
                .Build())
            {
                consumer.Subscribe(Topics);

                try
                {
                    while (true)
                    {
                        try
                        {
                            var consumeResult = consumer.Consume(CnclToken);

                            if (consumeResult.IsPartitionEOF)
                            {
                                Console.WriteLine(
                                    $"Reached end of topic {consumeResult.Topic}, partition {consumeResult.Partition}, offset {consumeResult.Offset}.");

                                continue;
                            }

                            Console.WriteLine($"Received message at {consumeResult.TopicPartitionOffset}: {consumeResult.Key}:{consumeResult.Value}");
                            ReaderCallback(consumeResult);

                            if (consumeResult.Offset % commitPeriod == 0)
                            {
                                // The Commit method sends a "commit offsets" request to the Kafka
                                // cluster and synchronously waits for the response. This is very
                                // slow compared to the rate at which the consumer is capable of
                                // consuming messages. A high performance application will typically
                                // commit offsets relatively infrequently and be designed handle
                                // duplicate messages in the event of failure.
                                try
                                {
                                    consumer.Commit(consumeResult);
                                }
                                catch (KafkaException e)
                                {
                                    Console.WriteLine($"Commit error: {e.Error.Reason}");
                                }
                            }
                        }
                        catch (ConsumeException e)
                        {
                            Console.WriteLine($"Consume error: {e.Error.Reason}");
                        }
                        if (ReadOne)
                            break;
                    }
                }
                catch (OperationCanceledException)
                {
                    Console.WriteLine("Closing consumer.");
                    consumer.Close();
                }
            }
        }
    }
}