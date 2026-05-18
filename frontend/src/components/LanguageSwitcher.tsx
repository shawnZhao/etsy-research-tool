"use client";

import React from "react";
import { useTranslation } from "../lib/i18n/context";

export function LanguageSwitcher() {
  const { locale, setLocale } = useTranslation();

  const toggle = () => {
    setLocale(locale === "en" ? "zh" : "en");
  };

  return (
    <button
      onClick={toggle}
      className="text-sm px-2 py-1 border border-gray-300 rounded text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer"
    >
      {locale === "en" ? "中文" : "EN"}
    </button>
  );
}
