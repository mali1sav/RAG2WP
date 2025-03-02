"""Constants for the RAG application."""

# Define site-specific edit URLs
SITE_EDIT_URLS = {
    "BITCOINIST": "https://bitcoinist.com/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "NEWSBTC": "https://www.newsbtc.com/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "ICOBENCH": "https://icobench.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "CRYPTONEWS": "https://cryptonews.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "INSIDEBITCOINS": "https://insidebitcoins.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "COINDATAFLOW": "https://coindataflow.com/th/blog/wp-admin/post.php?post={post_id}&action=edit&classic-editor"
}

# Promotional Images Data Structure
PROMOTIONAL_IMAGES = {
    "Best Wallet": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/best-wallet-1024x952-1.png",
        "alt": "Best Wallet",
        "width": "600",
        "height": "558"
    },
    "Solaxy": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/solaxy-1.png",
        "alt": "Solaxy Thailand",
        "width": "600",
        "height": "520"
    },
    "BTC Bull Token": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/btc-bull-token.png",
        "alt": "BTC Bull Token",
        "width": "600",
        "height": "408"
    },
    "Mind of Pepe": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/mind-of-pepe-e1740672348698.png",
        "alt": "Mind of Pepe",
        "width": "600",
        "height": "490"
    },
    "Meme Index": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/memeindex.png",
        "alt": "Meme Index",
        "width": "600",
        "height": "468"
    },
    "Catslap": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/catslap.png",
        "alt": "Catslap Token",
        "width": "600",
        "height": "514"
    }
}

# Affiliate Links Data Structure
AFFILIATE_LINKS = {
    "ICOBENCH": {
        "Best Wallet": "https://icobench.com/th/visit/bestwallettoken",
        "Solaxy": "https://icobench.com/th/visit/solaxy",
        "BTC Bull Token": "https://icobench.com/th/visit/bitcoin-bull",
        "Mind of Pepe": "https://icobench.com/th/visit/mindofpepe",
        "Meme Index": "https://icobench.com/th/visit/memeindex",
        "Catslap": "https://icobench.com/th/visit/catslap"
    },
    "BITCOINIST": {
        "Best Wallet": "https://bs_332b25fb.bitcoinist.care/",
        "Solaxy": "https://bs_ddfb0f8c.bitcoinist.care/",
        "BTC Bull Token": "https://bs_919798f4.bitcoinist.care/",
        "Mind of Pepe": "https://bs_1f5417eb.bitcoinist.care/",
        "Meme Index": "https://bs_89e992a3.bitcoinist.care",
        "Catslap": "https://bs_362f7e64.bitcoinist.care/"
    },
    "COINDATAFLOW": {
        "Best Wallet": "https://bs_75a55063.Cryptorox.care",
        "Solaxy": "https://bs_baf1ac7c.Cryptorox.care",
        "BTC Bull Token": "https://bs_d3f9bf50.Cryptorox.care",
        "Mind of Pepe": "https://bs_770fab4c.Cryptorox.care",
        "Meme Index": "https://bs_89204fe5.Cryptorox.care",
        "Best Wallet Token": "https://bs_9f0cd602.Cryptorox.care",
        "Catslap": "https://bs_7425c4d9.Cryptorox.care"
    },
    "CRYPTONEWS": {
        "Best Wallet": "https://bestwallettoken.com/th?tid=156",
        "Solaxy": "https://solaxy.io/th/?tid=156",
        "BTC Bull Token": "https://btcbulltoken.com/th?tid=156",
        "Mind of Pepe": "https://mindofpepe.com/th?tid=156",
        "Meme Index": "https://memeindex.com/?tid=156",
        "Catslap": "https://catslaptoken.com/th?tid=156"
    },
    "INSIDEBITCOINS": {
        "Best Wallet": "https://insidebitcoins.com/th/visit/best-wallet-token",
        "Solaxy": "https://insidebitcoins.com/th/visit/solaxy",
        "BTC Bull Token": "https://insidebitcoins.com/th/visit/bitcoin-bull",
        "Mind of Pepe": "https://insidebitcoins.com/th/visit/mindofpepe",
        "Meme Index": "https://insidebitcoins.com/th/visit/memeindex",
        "Catslap": "https://insidebitcoins.com/th/visit/catslap"
    }
}

# Default values
DEFAULT_URL = ""
DEFAULT_KEYWORD = "Bitcoin"
DEFAULT_NEWS_ANGLE = ""
DEFAULT_SECTION_COUNT = 3
