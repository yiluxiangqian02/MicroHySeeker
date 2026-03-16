import { motion } from 'framer-motion';
import { BookOpen, FlaskConical, MessageSquare, Database, Sparkles, ArrowRightCircle } from 'lucide-react';
import ChatWindow from '@/components/ChatWindow';

export function KnowledgeHub() {
  return (
    <motion.div
      className="space-y-6 p-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-indigo-900 to-cyan-800 p-6 text-white shadow-sm">
        <div className="grid gap-6 lg:grid-cols-[1.35fr,1fr] lg:items-center">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-100">Knowledge Management</p>
            <h1 className="mt-3 text-3xl font-bold">知识管理 / 知识库 Chat</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-cyan-50/90">
              这里是面向实验工作的知识入口，不再只是“有个 Chat 按钮”。现在它至少具备独立页面、稳定消息流、清晰状态提示、实验上下文和 fallback mock flow。
            </p>
            <div className="mt-5 flex flex-wrap gap-3 text-xs text-cyan-50/90">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">可直接输入并发送消息</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">后端异常时自动 fallback</span>
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">强调实验上下文，而不是普通闲聊</span>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            {[
              { icon: FlaskConical, title: '问当前实验', desc: '带着 step 上下文追问 technique、参数和风险点。' },
              { icon: Database, title: '问历史实验', desc: '把最近 run 当作经验库来查相似方案和异常。' },
              { icon: BookOpen, title: '问知识库', desc: '把文档、方法卡片和实验经验汇成同一个入口。' },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Icon className="h-4 w-4" />
                    {item.title}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-cyan-50/85">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.72fr,1.28fr]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 text-slate-900">
              <MessageSquare className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold">现在能怎么用</h2>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600">
              <li>• 围绕某个 step 提问：例如“这个 echem 步骤为什么先用 CV？”</li>
              <li>• 围绕运行异常提问：例如“transfer 卡住时优先看什么？”</li>
              <li>• 围绕下一轮设计提问：例如“结合最近实验，下一轮先改哪个变量？”</li>
              <li>• 围绕历史经验提问：例如“最近和 EIS 相关的 run 有什么共性？”</li>
            </ul>
          </div>

          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-violet-900">
              <Sparkles className="h-5 w-5" />
              <h2 className="text-lg font-semibold">这次补齐的可用性</h2>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-violet-900">
              <li>• 欢迎语 + quick actions，不再是空白聊天框。</li>
              <li>• 明确状态提示：连接中 / 在线 / fallback / 错误。</li>
              <li>• 本地历史兜底，后端不通也能持续展示对话。</li>
              <li>• 实验上下文卡片让用户知道它服务于实验，而不是泛聊天。</li>
            </ul>
          </div>

          <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-5 shadow-sm">
            <div className="flex items-center gap-2 text-cyan-900">
              <ArrowRightCircle className="h-5 w-5" />
              <h2 className="text-lg font-semibold">下一阶段最值得接的是真后端能力</h2>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-cyan-900">
              <li>• 实验详情页真实注入 step / run / 最近结果摘要。</li>
              <li>• 返回 citations、相似实验和结构化建议卡片。</li>
              <li>• 把当前会话和 experiment_id 绑定，而不只是全局历史。</li>
            </ul>
          </div>
        </div>

        <ChatWindow
          mode="embedded"
          contextItems={['当前实验上下文', '知识库文档 / 方法经验', '历史实验 / 最近 run', '失败复盘 / 下一轮建议']}
          experimentContext={{
            experimentName: 'Electrochemical sensing workflow（占位）',
            stage: '等待接入当前 experiment / step 信息',
            objective: '帮助用户围绕当前实验提问，而不是脱离实验背景闲聊。',
            latestObservation: '前端已显示实验上下文卡；后端暂未返回真实 run 摘要。',
            nextSuggestion: '可直接问 technique 选择、异常排查、相似实验或下一轮变量。',
          }}
        />
      </section>
    </motion.div>
  );
}
