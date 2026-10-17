interface BrowserSnaphsotProps {
  src: string;
}

export function BrowserSnapshot({ src }: BrowserSnaphsotProps) {
  const { t } = useTranslation("openhands");

  return (
    <img
      src={src}
      className="block w-full h-auto"
      alt={t(I18nKey.BROWSER$SCREENSHOT_ALT)}
    />
  );
}
