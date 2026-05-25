import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title:       "سياسة الخصوصية — تبيان الطبي",
  description: "سياسة خصوصية منصة تبيان الطبي وفق أحكام نظام حماية البيانات الشخصية PDPL",
}

const LAST_UPDATED = "24 مايو 2026"
const CONTACT_EMAIL = "privacy@tibyan.health"

export default function PrivacyPage() {
  return (
    <main
      dir="rtl"
      className="min-h-screen bg-background text-foreground font-cairo"
    >
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="max-w-3xl mx-auto px-6 py-6 flex items-center justify-between">
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            → العودة للرئيسية
          </Link>
          <div className="text-right">
            <h1 className="text-xl font-bold text-foreground">سياسة الخصوصية</h1>
            <p className="text-xs text-muted-foreground mt-0.5">آخر تحديث: {LAST_UPDATED}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 py-12 space-y-10">

        {/* Disclaimer */}
        <div className="p-5 rounded-2xl bg-warning/8 border border-warning/20 text-right">
          <p className="text-sm font-bold text-warning mb-1">تنبيه طبي مهم</p>
          <p className="text-sm text-foreground leading-relaxed">
            تبيان الطبي أداة توعوية تعليمية فقط. <strong>لا تُغني نتائجها عن استشارة طبيب مختص.</strong>
            لا تعتمد على التفسيرات المعروضة لاتخاذ قرارات علاجية.
          </p>
        </div>

        <Section title="1. من نحن">
          <p>
            تبيان الطبي منصة رقمية مقرّها المملكة العربية السعودية تُقدّم خدمة تحليل التقارير المختبرية
            بالاستعانة بالذكاء الاصطناعي. تعمل المنصة وفق أحكام{" "}
            <strong>نظام حماية البيانات الشخصية (PDPL)</strong> الصادر بالمرسوم الملكي رقم م/19
            ولوائح الهيئة الوطنية لإدارة البيانات ومركز المعلومات الوطني (NDMO).
          </p>
        </Section>

        <Section title="2. البيانات التي نجمعها">
          <ul className="space-y-3">
            <DataRow
              label="ملفات التحاليل"
              detail="صور أو PDF ترفعها لتحليلها — تُعالَج مؤقتاً ولا تُخزَّن بشكل دائم مرتبطة بهويتك"
            />
            <DataRow
              label="بيانات الجلسة"
              detail="معرّف جلسة عشوائي مجهول الهوية لربط المحادثات والتحاليل السابقة"
            />
            <DataRow
              label="سجلات الاستخدام"
              detail="وقت الطلب ونوعه فقط — بدون محتوى الملفات — لأغراض الأداء والأمان"
            />
            <DataRow
              label="اسم الملف الشخصي"
              detail="إذا أنشأت ملفات عائلية (اختياري) — اسم فقط، بدون بيانات هوية"
            />
          </ul>
        </Section>

        <Section title="3. ما لا نجمعه">
          <ul className="list-disc list-inside space-y-1.5 text-sm text-foreground leading-relaxed">
            <li>لا نجمع الاسم الحقيقي أو رقم الهوية أو رقم الجوال</li>
            <li>لا نربط التحاليل بهوية شخصية محددة</li>
            <li>لا نشارك أي بيانات مع جهات تسويقية</li>
            <li>لا نستخدم ملفاتك لتدريب نماذج الذكاء الاصطناعي</li>
          </ul>
        </Section>

        <Section title="4. كيف نستخدم بياناتك">
          <ul className="list-disc list-inside space-y-1.5 text-sm text-foreground leading-relaxed">
            <li>معالجة ملف التحليل وإعادة النتيجة إليك فوراً</li>
            <li>حفظ سجل تحاليلك السابقة في جلستك (يمكنك حذفه)</li>
            <li>تحسين أداء الخدمة عبر سجلات مجهولة الهوية</li>
            <li>رصد الأخطاء التقنية لضمان استمرارية الخدمة</li>
          </ul>
        </Section>

        <Section title="5. تخزين البيانات والمنطقة الجغرافية">
          <p>
            تُخزَّن البيانات على خوادم Supabase في منطقة{" "}
            <strong>الشرق الأوسط (AWS me-central-1)</strong> داخل المملكة العربية السعودية،
            مما يضمن توافق البيانات مع متطلبات PDPL الخاصة بالمعالجة المحلية.
          </p>
          <p className="mt-3">
            <strong>مدة الاحتفاظ:</strong> تُحذف التحاليل والمحادثات تلقائياً بعد{" "}
            <strong>12 شهراً</strong> من تاريخ آخر نشاط.
          </p>
        </Section>

        <Section title="6. الأطراف الثالثة">
          <div className="space-y-3">
            <ThirdParty name="Groq" purpose="تشغيل نموذج اللغة الكبير (تحليل النصوص)" region="USA" note="لا يُحفظ محتوى الطلبات" />
            <ThirdParty name="Google Cloud Vision" purpose="استخراج النصوص من الصور (OCR)" region="USA" note="معالجة مؤقتة فقط" />
            <ThirdParty name="Cohere" purpose="إعادة ترتيب نتائج البحث (Reranking)" region="USA" note="نصوص مجهولة الهوية" />
            <ThirdParty name="Sentry" purpose="رصد الأخطاء التقنية" region="USA" note="بدون معلومات شخصية (PII معطّل)" />
            <ThirdParty name="Vercel" purpose="استضافة الواجهة الأمامية" region="Global CDN" note="لا تصل لمحتوى التحاليل" />
          </div>
        </Section>

        <Section title="7. حقوقك وفق PDPL">
          <ul className="space-y-3">
            <Right title="الاطلاع" detail="طلب معرفة البيانات المخزّنة المرتبطة بجلستك" />
            <Right title="التصحيح" detail="تعديل أي بيانات خاطئة" />
            <Right title="الحذف" detail="طلب حذف جميع بياناتك نهائياً خلال 72 ساعة" />
            <Right title="الاعتراض" detail="الاعتراض على أي معالجة لا تراها ضرورية" />
          </ul>
          <p className="mt-4 text-sm text-muted-foreground">
            لممارسة أي من هذه الحقوق، تواصل معنا على:{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-primary hover:underline">
              {CONTACT_EMAIL}
            </a>
          </p>
        </Section>

        <Section title="8. الأمان التقني">
          <ul className="list-disc list-inside space-y-1.5 text-sm text-foreground leading-relaxed">
            <li>جميع الاتصالات مشفّرة بـ TLS 1.3</li>
            <li>لا تُخزَّن ملفات التحاليل الأصلية بعد المعالجة</li>
            <li>مفاتيح API مخزّنة في متغيرات البيئة المشفّرة (Railway Secrets)</li>
            <li>رصد الأخطاء بدون بيانات شخصية (<code className="text-xs bg-muted px-1 rounded">send_default_pii=False</code>)</li>
          </ul>
        </Section>

        <Section title="9. ملفات تعريف الارتباط (Cookies)">
          <p>
            نستخدم ملفات تعريف الارتباط الضرورية فقط لإدارة الجلسة والمصادقة عبر Supabase Auth.
            لا نستخدم ملفات تتبع تسويقية أو تحليلية خارجية.
          </p>
        </Section>

        <Section title="10. التعديلات على هذه السياسة">
          <p>
            قد نُحدّث هذه السياسة بما يتوافق مع التطورات التنظيمية أو التقنية.
            سيُعلَن عن أي تغيير جوهري بإشعار واضح داخل المنصة قبل 14 يوماً من تطبيقه.
          </p>
        </Section>

        {/* Contact */}
        <div className="p-6 rounded-2xl bg-card border border-border text-right">
          <p className="text-sm font-bold text-foreground mb-1">تواصل معنا</p>
          <p className="text-sm text-muted-foreground">
            لأي استفسار يتعلق بالخصوصية أو حماية البيانات:{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-primary hover:underline">
              {CONTACT_EMAIL}
            </a>
          </p>
        </div>

      </div>
    </main>
  )
}

/* ─── Helper components ─── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="text-right">
      <h2 className="text-base font-bold text-foreground mb-3 pb-2 border-b border-border">
        {title}
      </h2>
      <div className="text-sm text-foreground leading-relaxed space-y-2">{children}</div>
    </section>
  )
}

function DataRow({ label, detail }: { label: string; detail: string }) {
  return (
    <li className="flex gap-3 items-start">
      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary mt-0.5 shrink-0">
        {label}
      </span>
      <span className="text-sm text-muted-foreground">{detail}</span>
    </li>
  )
}

function ThirdParty({ name, purpose, region, note }: { name: string; purpose: string; region: string; note: string }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl bg-muted/30 border border-border">
      <div className="text-right flex-1">
        <p className="text-sm font-bold text-foreground">{name}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{purpose}</p>
        <p className="text-[10px] text-muted-foreground/70 mt-1">المنطقة: {region} — {note}</p>
      </div>
    </div>
  )
}

function Right({ title, detail }: { title: string; detail: string }) {
  return (
    <li className="flex gap-3 items-start">
      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-success/10 text-success mt-0.5 shrink-0">
        {title}
      </span>
      <span className="text-sm text-muted-foreground">{detail}</span>
    </li>
  )
}
