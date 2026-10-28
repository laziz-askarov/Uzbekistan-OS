/**
 * Editorial photographs for the public site. Every file under public/photos
 * is listed here with its author and licence; the footer prints these credits.
 * Sourced from Wikimedia Commons on 2026-10-28; replace with Kebab Travel
 * photography as it becomes available.
 */
export type Photo = {
  src: string;
  alt: string;
  caption: string;
  width: number;
  height: number;
  credit: { author: string; license: string; source: string };
};

export const PHOTOS = {
  bukharaPoiKalyanDusk: {
    src: "/photos/bukhara-poi-kalyan-dusk.jpg",
    alt: "The Kalon minaret and Mir-i-Arab madrasa in Bukhara at dusk, lit from below under a deep blue sky",
    caption: "Po-i-Kalyan, Bukhara",
    width: 1600,
    height: 1068,
    credit: {
      author: "Pixoos",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:Bukhara_by_Pouria_Afkhami_aka_pixoos_01.jpg",
    },
  },
  samarkandRegistanNight: {
    src: "/photos/samarkand-registan-night.jpg",
    alt: "The three madrasas of the Registan in Samarkand lit at night",
    caption: "Registan, Samarkand",
    width: 1600,
    height: 949,
    credit: {
      author: "Kraftabbas",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:%D0%A1%D0%B0%D0%BC%D0%B0%D1%80%D0%BA%D0%B0%D0%BD%D0%B4._%D0%9F%D0%BB%D0%BE%D1%89%D0%B0%D0%B4%D1%8C-%D0%A0%D0%B5%D0%B3%D0%B8%D1%81%D1%82%D0%B0%D0%BD.jpg",
    },
  },
  bukharaKalonMinaretDusk: {
    src: "/photos/bukhara-kalon-minaret-dusk.jpg",
    alt: "The Kalon minaret in Bukhara at dusk, seen from the square below",
    caption: "Kalon minaret, Bukhara",
    width: 1600,
    height: 1068,
    credit: {
      author: "Pixoos",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:Bukhara_by_Pouria_Afkhami_aka_pixoos_02.jpg",
    },
  },
  khivaKonyaArkNight: {
    src: "/photos/khiva-konya-ark-night.jpg",
    alt: "The gate of the Konya Ark fortress and Kalta Minor in Khiva, lit at night",
    caption: "Konya Ark, Khiva",
    width: 1600,
    height: 1007,
    credit: {
      author: "Bgag",
      license: "CC0",
      source: "https://commons.wikimedia.org/wiki/File:Konya_Ark_gate.jpg",
    },
  },
  barsakelmesSunset: {
    src: "/photos/barsakelmes-sunset.jpg",
    alt: "A lone figure on the Barsakelmes salt flat in Karakalpakstan at sunset",
    caption: "Barsakelmes, Karakalpakstan",
    width: 1600,
    height: 1066,
    credit: {
      author: "Dilmurad91",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:%D0%9A%D0%B0%D1%80%D0%B0%D0%BA%D0%B0%D0%BB%D0%BF%D0%B0%D0%BA_%D0%BD%D0%B0_%D0%91%D0%B0%D1%80%D1%81%D0%B0%D0%BA%D0%B5%D0%BB%D1%8C%D0%BC%D0%B5%D1%81.jpg",
    },
  },
  moynaqShipGraveyard: {
    src: "/photos/moynaq-ship-graveyard.jpg",
    alt: "A rusting fishing boat on the sand of the former Aral Sea bed at Moynaq",
    caption: "Moynaq, the former Aral Sea",
    width: 1600,
    height: 1066,
    credit: {
      author: "Koshkinhome",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:Aral_Sea_Moynaq_Karakalpakstan_Uzbekistan_September_2025_Ph_Khusen_Rustamov-_12.jpg",
    },
  },
  kyzylkumYurtsNight: {
    src: "/photos/kyzylkum-yurts-night.jpg",
    alt: "Yurts under a full moon in the Kyzylkum desert",
    caption: "Kyzylkum desert",
    width: 1600,
    height: 1067,
    credit: {
      author: "Carsten Siegel",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:Kazakh_yurts_at_night_in_the_Kyzylkum_desert,_Uzbekistan.jpg",
    },
  },
  pskemRiverMorning: {
    src: "/photos/pskem-river-morning.jpg",
    alt: "Morning light over the Pskem river valley in the Tashkent mountains",
    caption: "Pskem valley",
    width: 1600,
    height: 1064,
    credit: {
      author: "Arina Pan",
      license: "CC BY-SA 4.0",
      source:
        "https://commons.wikimedia.org/wiki/File:%D0%A3%D1%82%D1%80%D0%BE_%D0%BD%D0%B0_%D1%80%D0%B5%D0%BA%D0%B5_%D0%9F%D1%81%D0%BA%D0%B5%D0%BC.jpg",
    },
  },
  chorsuBazaarTashkent: {
    src: "/photos/chorsu-bazaar-tashkent.jpg",
    alt: "Stalls and shoppers under the dome of Chorsu bazaar in Tashkent",
    caption: "Chorsu bazaar, Tashkent",
    width: 1400,
    height: 1050,
    credit: {
      author: "Dan Lundberg",
      license: "CC BY-SA 2.0",
      source:
        "https://commons.wikimedia.org/wiki/File:Chorsu_Bazaar_20141003_Uzbekistan_0840_Tashkent_(16257413122).jpg",
    },
  },
} as const satisfies Record<string, Photo>;

export const PHOTO_LIST: readonly Photo[] = Object.values(PHOTOS);
