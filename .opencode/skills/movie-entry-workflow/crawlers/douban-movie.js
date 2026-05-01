/**
 * 豆瓣电影爬虫
 * 
 * 输入：豆瓣电影 ID
 * 输出：raw-douban.json
 */

const playwright = require('playwright');

async function crawlDoubanMovie(options) {
  const { id, cookie, output = 'raw-douban.json', timeout = 30000, verbose = false } = options;
  
  const sourceUrl = `https://movie.douban.com/subject/${id}/`;
  const crawledAt = new Date().toISOString();
  
  const result = {
    source: 'douban',
    sourceUrl,
    crawledAt,
    crawlerScript: 'douban-movie.js',
    data: {},
    errors: [],
    warnings: []
  };
  
  const browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext();
  
  // 设置 cookie
  if (cookie) {
    const cookies = parseCookie(cookie);
    await context.addCookies(cookies);
  }
  
  const page = await context.newPage();
  page.setDefaultTimeout(timeout);
  
  try {
    // 1. 主页面 - 基本信息
    if (verbose) console.log('爬取主页面...');
    await page.goto(sourceUrl, { waitUntil: 'networkidle' });
    
    result.data.title = await extractText(page, 'h1 span[property="v:itemreviewed"]');
    result.data.year = await extractYear(page);
    result.data.originalTitle = await extractOriginalTitle(page);
    result.data.genre = await extractArray(page, 'span[property="v:genre"]');
    result.data.country = await extractInfo(page, '制片国家/地区');
    result.data.language = await extractInfo(page, '语言');
    result.data.runtime = await extractRuntime(page);
    result.data.releaseDate = await extractReleaseDate(page);
    result.data.aka = await extractAka(page);
    result.data.imdbId = await extractImdbId(page);
    result.data.doubanId = id;
    result.data.doubanRating = await extractRating(page);
    result.data.doubanVotes = await extractVotes(page);
    result.data.synopsis = await extractSynopsis(page);
    
    // 2. 演职员页面
    if (verbose) console.log('爬取演职员页面...');
    await page.goto(`${sourceUrl}celebrities`, { waitUntil: 'networkidle' });
    
    result.data.director = await extractDirector(page);
    result.data.writer = await extractWriter(page);
    result.data.cast = await extractCast(page);
    
    // 3. 图片页面
    if (verbose) console.log('爬取图片页面...');
    await page.goto(`${sourceUrl}photos?type=R`, { waitUntil: 'networkidle' });
    result.data.posterUrls = await extractImageUrls(page);
    
    await page.goto(`${sourceUrl}photos?type=S`, { waitUntil: 'networkidle' });
    result.data.stillUrls = await extractImageUrls(page);
    
    await page.goto(`${sourceUrl}photos?type=W`, { waitUntil: 'networkidle' });
    result.data.wallpaperUrls = await extractImageUrls(page);
    
    // 4. 视频页面
    if (verbose) console.log('爬取视频页面...');
    await page.goto(`${sourceUrl}trailer`, { waitUntil: 'networkidle' });
    result.data.videos = await extractVideos(page);
    
    // 5. 影评页面
    if (verbose) console.log('爬取影评页面...');
    await page.goto(`${sourceUrl}reviews`, { waitUntil: 'networkidle' });
    result.data.reviews = await extractReviews(page);
    
    // 6. 相似推荐
    if (verbose) console.log('爬取相似推荐...');
    await page.goto(sourceUrl, { waitUntil: 'networkidle' });
    result.data.similar = await extractSimilar(page);
    
  } catch (error) {
    result.errors.push({
      stage: 'crawling',
      message: error.message,
      url: page.url()
    });
  }
  
  await browser.close();
  
  // 写入输出文件
  if (output) {
    const fs = require('fs');
    fs.writeFileSync(output, JSON.stringify(result, null, 2));
    if (verbose) console.log(`输出写入: ${output}`);
  }
  
  return result;
}

// 辅助函数

function parseCookie(cookieString) {
  return cookieString.split(';').map(c => {
    const [name, value] = c.trim().split('=');
    return { name, value, domain: '.douban.com' };
  });
}

async function extractText(page, selector) {
  try {
    return await page.locator(selector).textContent();
  } catch {
    return null;
  }
}

async function extractYear(page) {
  try {
    const text = await page.locator('h1 .year').textContent();
    return parseInt(text.match(/\d{4}/)[0]);
  } catch {
    return null;
  }
}

async function extractOriginalTitle(page) {
  try {
    // 尝试从页面提取原名
    const info = await page.locator('#info').textContent();
    const match = info.match(/原名[：:]\s*(.+)/);
    return match ? match[1].trim() : null;
  } catch {
    return null;
  }
}

async function extractArray(page, selector) {
  try {
    const elements = await page.locator(selector).all();
    return elements.map(el => el.textContent());
  } catch {
    return [];
  }
}

async function extractInfo(page, label) {
  try {
    const info = await page.locator('#info').textContent();
    const match = info.match(new RegExp(`${label}[：:]\\s*(.+?)(?=\\n|\\s{2,})`));
    return match ? match[1].trim() : null;
  } catch {
    return null;
  }
}

async function extractRuntime(page) {
  try {
    const text = await page.locator('span[property="v:runtime"]').textContent();
    return parseInt(text);
  } catch {
    return null;
  }
}

async function extractReleaseDate(page) {
  try {
    const elements = await page.locator('span[property="v:initialReleaseDate"]').all();
    return elements.map(el => {
      const text = el.textContent();
      const match = text.match(/(\d{4}-\d{2}-\d{2})\((.+)\)/);
      if (match) {
        return { date: match[1], location: match[2] };
      }
      return { date: text, location: '' };
    });
  } catch {
    return [];
  }
}

async function extractAka(page) {
  try {
    const info = await page.locator('#info').textContent();
    const match = info.match(/又名[：:]\s*(.+?)(?=\\n|\\s{2,}|制片)/);
    if (match) {
      return match[1].split('/').map(s => s.trim());
    }
    return [];
  } catch {
    return [];
  }
}

async function extractImdbId(page) {
  try {
    const link = await page.locator('a[href*="imdb.com/title"]').getAttribute('href');
    const match = link.match(/tt\d+/);
    return match ? match[0] : null;
  } catch {
    return null;
  }
}

async function extractRating(page) {
  try {
    const text = await page.locator('strong[property="v:average"]').textContent();
    return parseFloat(text);
  } catch {
    return null;
  }
}

async function extractVotes(page) {
  try {
    const text = await page.locator('span[property="v:votes"]').textContent();
    return parseInt(text);
  } catch {
    return null;
  }
}

async function extractSynopsis(page) {
  try {
    const text = await page.locator('span[property="v:summary"]').textContent();
    return { text: text.trim(), note: '' };
  } catch {
    return { text: '', note: '' };
  }
}

async function extractDirector(page) {
  try {
    const elements = await page.locator('.director a').all();
    return elements.map(el => ({
      name: el.textContent(),
      nameEn: '',
      avatar: '',
      works: []
    }));
  } catch {
    return [];
  }
}

async function extractWriter(page) {
  try {
    const elements = await page.locator('.writer a').all();
    return elements.map(el => ({
      name: el.textContent(),
      nameEn: '',
      role: '编剧'
    }));
  } catch {
    return [];
  }
}

async function extractCast(page) {
  try {
    const elements = await page.locator('.actor a').all();
    const roles = await page.locator('.actor .role').all();
    return elements.map((el, i) => ({
      name: el.textContent(),
      nameEn: '',
      role: roles[i] ? roles[i].textContent().replace(/饰\s*/, '') : '',
      avatar: ''
    }));
  } catch {
    return [];
  }
}

async function extractImageUrls(page) {
  try {
    const elements = await page.locator('.cover img').all();
    return elements.map(el => el.getAttribute('src'));
  } catch {
    return [];
  }
}

async function extractVideos(page) {
  try {
    const elements = await page.locator('.video-item').all();
    return elements.map(el => ({
      title: el.locator('.title').textContent(),
      duration: el.locator('.duration').textContent(),
      thumbnail: el.locator('img').getAttribute('src'),
      url: el.locator('a').getAttribute('href')
    }));
  } catch {
    return [];
  }
}

async function extractReviews(page) {
  try {
    const elements = await page.locator('.review-item').all();
    return elements.slice(0, 5).map(el => ({
      source: '豆瓣',
      author: el.locator('.author').textContent(),
      date: el.locator('.date').textContent(),
      rating: el.locator('.rating').textContent(),
      content: el.locator('.short').textContent()
    }));
  } catch {
    return [];
  }
}

async function extractSimilar(page) {
  try {
    const elements = await page.locator('.recommend-item').all();
    return elements.map(el => ({
      title: el.locator('.title').textContent(),
      rating: parseFloat(el.locator('.rating').textContent())
    }));
  } catch {
    return [];
  }
}

// CLI 入口
if (require.main === module) {
  const args = require('minimist')(process.argv.slice(2));
  crawlDoubanMovie({
    id: args.id,
    cookie: args.cookie,
    output: args.output,
    timeout: args.timeout,
    verbose: args.verbose
  }).then(result => {
    console.log(`爬取完成: ${result.errors.length} 错误, ${result.warnings.length} 警告`);
  });
}

module.exports = { crawlDoubanMovie };