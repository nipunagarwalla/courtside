// IOC country codes (as used by tennis data) → ISO 3166-1 alpha-2, for flag emoji.
const IOC_TO_ISO2: Record<string, string> = {
  ALG: "DZ", ARG: "AR", ARM: "AM", AUS: "AU", AUT: "AT", AZE: "AZ",
  BAR: "BB", BEL: "BE", BIH: "BA", BLR: "BY", BOL: "BO", BRA: "BR",
  BUL: "BG", CAN: "CA", CHI: "CL", CHN: "CN", COL: "CO", CRC: "CR",
  CRO: "HR", CUB: "CU", CYP: "CY", CZE: "CZ", DEN: "DK", DOM: "DO",
  ECU: "EC", EGY: "EG", ESA: "SV", ESP: "ES", EST: "EE", FIN: "FI",
  FRA: "FR", GBR: "GB", GEO: "GE", GER: "DE", GHA: "GH", GRE: "GR",
  GUA: "GT", HAI: "HT", HKG: "HK", HON: "HN", HUN: "HU", INA: "ID",
  IND: "IN", IRL: "IE", ISL: "IS", ISR: "IL", ITA: "IT", JAM: "JM",
  JPN: "JP", KAZ: "KZ", KEN: "KE", KGZ: "KG", KOR: "KR", LAT: "LV",
  LBN: "LB", LIB: "LB", LTU: "LT", LUX: "LU", MAR: "MA", MAS: "MY",
  MDA: "MD", MEX: "MX", MON: "MC", NCA: "NI", NED: "NL", NGR: "NG",
  NOR: "NO", NZL: "NZ", PAK: "PK", PAN: "PA", PAR: "PY", PER: "PE",
  PHI: "PH", POL: "PL", POR: "PT", PUR: "PR", ROU: "RO", RSA: "ZA",
  RUS: "RU", SRB: "RS", SLO: "SI", SVK: "SK", SUI: "CH", SWE: "SE",
  THA: "TH", TJK: "TJ", TKM: "TM", TPE: "TW", TTO: "TT", TUN: "TN",
  TUR: "TR", UKR: "UA", URU: "UY", USA: "US", UZB: "UZ", VEN: "VE",
  VIE: "VN", ZIM: "ZW",
};

export function countryFlag(ioc: string | null | undefined): string {
  if (!ioc) return "";
  const iso2 = IOC_TO_ISO2[ioc.toUpperCase()];
  if (!iso2) return "";
  return String.fromCodePoint(
    ...[...iso2].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65)
  );
}
