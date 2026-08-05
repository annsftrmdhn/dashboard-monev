# Configuration Settings for Contact Center Monitoring Dashboard

# SLA threshold in seconds (e.g., 300 seconds = 5 minutes)
DEFAULT_SLA_THRESHOLD = 300

# Operational hours (WIB)
OPERATIONAL_HOURS_START = 8
OPERATIONAL_HOURS_END = 17

# Agent target occupancy rate
TARGET_OCCUPANCY = 0.85

# AHT / handle time bounds (seconds)
AHT_MIN_SECONDS = 1
AHT_MAX_SECONDS = 24 * 3600  # 24 jam — outlier diabaikan

# Fallback rata-rata handle time untuk staffing jika AHT tidak terhitung (10 menit)
STAFFING_FALLBACK_AHT_SECONDS = 600

# Wrap-up agen setelah FRT (live chat / Created=Closed) — detik
STAFFING_WRAP_SECONDS = 480

# Batas maks handle time operasional untuk perhitungan staffing (20 menit)
STAFFING_AHT_MAX_SECONDS = 1200

# Sumbu X histogram FRT (menit)
FRT_HISTOGRAM_MAX_MINUTES = 150

# Default color mapping for sentiment categories
COLOR_MAP = {
    'positive': '#2ecc71',
    'Positive': '#2ecc71',
    'neutral': '#95a5a6',
    'Neutral': '#95a5a6',
    'negative': '#e74c3c',
    'Negative': '#e74c3c'
}

# Word lists for sentiment explanation
EXPLANATION_KEYWORDS = {
    'negatif': [
        'kecewa', 'kecewaan', 'mengecewakan', 'marah', 'kesal', 'jengkel',
        'buruk', 'parah', 'jelek', 'ancur', 'bobrok', 'rugi', 'salah',
        'scam', 'penipuan', 'hoax', 'fake', 'bohong', 'tipu',
        'lamban', 'lelet', 'terlalu lama', 'lambat sekali',
        'tidak jelas', 'sulit sekali', 'susah sekali', 'berbelit'
    ],
    'positif': [
        'terima kasih', 'makasih', 'thanks', 'thank', 'thx', 'tq',
        'terimakasih', 'trimakasih', 'trims', 'nuhun', 'matur',
        'puas', 'senang', 'suka', 'love', 'sip', 'oke', 'ok',
        'satisfied', 'happy', 'gembira', 'lega', 'syukur', 'alhamdulillah',
        'membantu', 'bermanfaat', 'berguna', 'informatif', 'jelas',
        'ramah', 'sopan', 'profesional', 'responsif', 'tanggap',
        'sabar', 'telaten', 'detail', 'kompeten',
        'cepat', 'lancar', 'smooth', 'efisien', 'tepat', 'sigap',
        'gesit', 'kilat', 'instan',
        'baik', 'bagus', 'mantap', 'keren', 'kereen', 'hebat',
        'luar biasa', 'excellent', 'great', 'good', 'nice', 'best',
        'top', 'perfect', 'sempurna', 'istimewa', 'amazing', 'awesome',
        'mudah', 'gampang', 'simpel', 'praktis', 'convenient',
        'recommend', 'rekomendasi', 'rekomendasikan', 'percaya',
        'terpercaya', 'andal', 'reliable',
        'solved', 'terselesaikan', 'selesai', 'berhasil', 'sukses',
        'teratasi', 'terjawab', 'beres', 'fix', 'done',
        'setuju', 'benar', 'betul', 'cocok', 'sesuai', 'pas'
    ]
}

TECHNICAL_STATUS_PATTERNS = [
    'penolakan', 'reject', 'tolak', 'ditolak', 'error', 'gagal',
    'pending', 'stuck', 'tertahan', 'spsa', 'sptnp', 'notul', 'npp', 'spjm', 'spbc'
]

POSITIVE_CONTEXT_PATTERNS = [
    'selamat pagi', 'selamat siang', 'selamat sore', 'selamat malam',
    'pagi bravo', 'bravo team', 'pagi pak', 'pagi bu', 'siang pak', 'sore pak',
    'assalamualaikum', 'halo', 'hello', 'dear', 'yth', 'admin',
    'mohon', 'tolong', 'mohon bantuannya', 'mohon dibantu', 'minta tolong',
    'mohon bantuan', 'mohon info', 'mohon informasi', 'mohon arahannya', 'mohon solusinya',
    'bisa dibantu', 'bisa bantu', 'minta bantuan', 'mohon petunjuk',
    'terima kasih', 'makasih', 'thanks', 'terimakasih', 'trims', 'thx',
    'ingin menanyakan', 'ingin bertanya', 'mau bertanya', 'mau tanya',
    'izin bertanya', 'izin tanya', 'boleh bertanya', 'boleh tanya',
    'mau menanyakan', 'permisi', 'perkenalkan',
    'sudah selesai', 'sudah beres', 'sudah clear', 'baik', 'siap', 'noted'
]

EMOTIONAL_NEGATIVE_PATTERNS = [
    'kecewa', 'kecewaan', 'mengecewakan', 'marah', 'kesal', 'jengkel',
    'lambat sekali', 'terlalu lama', 'buruk', 'parah', 'jelek', 'ancur',
    'scam', 'penipuan', 'bohong', 'tipu', 'hoax', 'bobrok',
    'komplain', 'protes', 'rugi', 'tidak kompeten', 'tidak bertanggung jawab'
]
