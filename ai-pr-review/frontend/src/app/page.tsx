'use client';

import { SubmitPRForm } from '@/components/SubmitPRForm';

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      {/* Hero */}
      <div className="mb-10 text-center">
        <h1 className="mb-3 text-4xl font-bold tracking-tight text-gray-900">
          AI PR Review
        </h1>
        <p className="mx-auto max-w-lg text-lg text-gray-600">
          输入 GitHub Pull Request 链接，AI 自动分析代码质量，
          生成详细的审核报告。
        </p>
      </div>

      {/* Form */}
      <SubmitPRForm />

      {/* Feature highlights */}
      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        <FeatureCard
          icon="🔍"
          title="代码质量分析"
          description="自动检测安全漏洞、性能问题、代码异味和设计缺陷"
        />
        <FeatureCard
          icon="⚡"
          title="AI 驱动"
          description="基于 DeepSeek V4 Pro，深度理解代码上下文和变更意图"
        />
        <FeatureCard
          icon="📋"
          title="结构化报告"
          description="按严重级别分类的问题清单，附带代码建议和示例"
        />
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-3 text-3xl">{icon}</div>
      <h3 className="mb-2 font-semibold text-gray-900">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
