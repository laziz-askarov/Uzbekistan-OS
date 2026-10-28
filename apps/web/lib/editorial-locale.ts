const en = {
  home: "Home",
  guides: "Guides",
  breadcrumb: "Breadcrumb",
  by: "By",
  published: "Published",
  updated: "Updated",
  languages: "Article languages",
  takeaways: "Key takeaways",
  faq: "Frequently asked questions",
  sources: "Sources and review trail",
  reviewedKnowledge: "Reviewed knowledge:",
  knowledgeReviewed: "Knowledge reviewed",
  markdown: "View machine-readable Markdown →",
  author: "About the author",
  version: "Editorial version",
  disclaimer:
    "This page is independent informational guidance and links to the sources reviewed for this edition.",
  country: "Uzbekistan",
  locale: "en_US",
  domains: {
    tourism: "Tourism",
    immigration: "Immigration",
    "business-registration": "Business registration",
    healthcare: "Healthcare",
    "everyday-living": "Everyday living",
  } as Record<string, string>,
  types: {
    article: "Article",
    guide: "Guide",
    platform_update: "Platform update",
    interview: "Interview",
  } as Record<string, string>,
};
type EditorialLabels = typeof en;
const uz: EditorialLabels = {
  home: "Bosh sahifa",
  guides: "Maqolalar",
  breadcrumb: "Sahifa yo‘li",
  by: "Muallif:",
  published: "E’lon qilingan:",
  updated: "Yangilangan:",
  languages: "Maqola tillari",
  takeaways: "Asosiy xulosalar",
  faq: "Ko‘p beriladigan savollar",
  sources: "Manbalar va tekshiruv ma’lumotlari",
  reviewedKnowledge: "Tekshirilgan ma’lumot:",
  knowledgeReviewed: "Ma’lumot tekshirilgan sana:",
  markdown: "Mashina o‘qiy oladigan Markdown nusxasi →",
  author: "Muallif haqida",
  version: "Maqola tahriri",
  disclaimer:
    "Bu sahifa mustaqil axborot materialidir. Unda ushbu tahrir uchun tekshirilgan manbalarga havolalar berilgan.",
  country: "O‘zbekiston",
  locale: "uz_UZ",
  domains: {
    tourism: "Turizm",
    immigration: "Immigratsiya",
    "business-registration": "Biznesni ro‘yxatdan o‘tkazish",
    healthcare: "Sog‘liqni saqlash",
    "everyday-living": "Kundalik hayot",
  },
  types: {
    article: "Maqola",
    guide: "Qo‘llanma",
    platform_update: "Platforma yangiligi",
    interview: "Suhbat",
  },
};
const ru: EditorialLabels = {
  home: "Главная",
  guides: "Статьи",
  breadcrumb: "Навигационная цепочка",
  by: "Автор:",
  published: "Опубликовано:",
  updated: "Обновлено:",
  languages: "Языковые версии статьи",
  takeaways: "Главное",
  faq: "Часто задаваемые вопросы",
  sources: "Источники и сведения о проверке",
  reviewedKnowledge: "Проверенные сведения:",
  knowledgeReviewed: "Дата проверки сведений:",
  markdown: "Машиночитаемая версия Markdown →",
  author: "Об авторе",
  version: "Редакция статьи",
  disclaimer:
    "Это независимый информационный материал со ссылками на источники, проверенные для данной редакции.",
  country: "Узбекистан",
  locale: "ru_RU",
  domains: {
    tourism: "Туризм",
    immigration: "Иммиграция",
    "business-registration": "Регистрация бизнеса",
    healthcare: "Здравоохранение",
    "everyday-living": "Повседневная жизнь",
  },
  types: {
    article: "Статья",
    guide: "Руководство",
    platform_update: "Новости платформы",
    interview: "Интервью",
  },
};
export function editorialLabels(language: string): EditorialLabels {
  return (
    ({ en, uz, ru } as Record<string, EditorialLabels>)[
      language.split("-")[0]
    ] ?? en
  );
}
