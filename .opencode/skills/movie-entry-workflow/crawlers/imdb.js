/**
 * IMDb 爬虫
 * 
 * 输入：IMDb ID (ttXXXXXXX)
 * 输出：raw-imdb.json
 */

const playwright = require('playwright');

async function crawlImdb(options) {
  const { id, output = 'raw-imdb.json', timeout = 30000, verbose = false } = options;
  
  const sourceUrl = `https://www.imdb.com/title/${id}/`;
  const crawledAt = new Date().toISOString();
  
  const result = {
    source: 'imdb',
    sourceUrl,
    crawledAt,
    crawlerScript: 'imdb.js',
    data: {},
    errors: [],
    warnings: []
  };
  
  const browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: 'en-US'
  });
  const page = await context.newPage();
  page.setDefaultTimeout(timeout);
  
  try {
    // 1. 主页面 - 基本信息
    if (verbose) console.log('爬取主页面...');
    await page.goto(sourceUrl, { waitUntil: 'networkidle' });
    
    result.data.originalTitle = await extractTitle(page);
    result.data.year = await extractYear(page);
    result.data.imdbId = id;
    result.data.imdbRating = await extractRating(page);
    result.data.imdbVotes = await extractVotes(page);
    result.data.genre = await extractGenre(page);
    result.data.runtime = await extractRuntime(page);
    result.data.synopsis = await extractSynopsis(page);
    
    // 2. 演职员页面
    if (verbose) console.log('爬取演职员页面...');
    await page.goto(`${sourceUrl}fullcredits`, { waitUntil: 'networkidle' });
    
    result.data.director = await extractDirector(page);
    result.data.writer = await extractWriter(page);
    result.data.cast = await extractCast(page);
    result.data.otherCast = await extractOtherCast(page);
    result.data.producer = await extractProducer(page);
    
    // 3. 图片页面
    if (verbose) console.log('爬取图片页面...');
    await page.goto(`${sourceUrl}mediaindex`, { waitUntil: 'networkidle' });
    result.data.imageUrls = await extractImageUrls(page);
    
    // 4. 视频页面
    if (verbose) console.log('爬取视频页面...');
    await page.goto(`${sourceUrl}videos`, { waitUntil: 'networkidle' });
    result.data.videos = await extractVideos(page);
    
    // 5. 相似推荐
    if (verbose) console.log('爬取相似推荐...');
    await page.goto(`${sourceUrl}similar`, { waitUntil: 'networkidle' });
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

async function extractTitle(page) {
  try {
    return await page.locator('h1').textContent();
  } catch {
    return null;
  }
}

async function extractYear(page) {
  try {
    const text = await page.locator('[data-testid="title-details-year"]').textContent();
    return parseInt(text.match(/\d{4}/)[0]);
  } catch {
    return null;
  }
}

async function extractRating(page) {
  try {
    const text = await page.locator('[data-testid="hero-rating-bar__aggregate-rating__score"]').first().textContent();
    return parseFloat(text);
  } catch {
    return null;
  }
}

async function extractVotes(page) {
  try {
    const text = await page.locator('[data-testid="hero-rating-bar__aggregate-rating__score"]').last().textContent();
    return parseInt(text.replace(/[^0-9]/g, ''));
  } catch {
    return null;
  }
}

async function extractGenre(page) {
  try {
    const elements = await page.locator('[data-testid="genres"]').locator('a').all();
    return elements.map(el => el.textContent());
  } catch {
    return [];
  }
}

async function extractRuntime(page) {
  try {
    const text = await page.locator('[data-testid="title-techspec_runtime"]').textContent();
    const match = text.match(/(\d+)\s*min/);
    return match ? parseInt(match[1]) : null;
  } catch {
    return null;
  }
}

async function extractSynopsis(page) {
  try {
    const text = await page.locator('[data-testid="plot"]').textContent();
    return { text: text.trim(), note: '' };
  } catch {
    return { text: '', note: '' };
  }
}

async function extractDirector(page) {
  try {
    const section = await page.locator('#fullcredits_content').locator('h4[data-testid="directors"]');
    const elements = await section.locator('a').all();
    return elements.map(el => ({
      name: '',
      nameEn: el.textContent(),
      avatar: '',
      works: []
    }));
  } catch {
    return [];
  }
}

async function extractWriter(page) {
  try {
    const section = await page.locator('#fullcredits_content').locator('h4[data-testid="writers"]');
    const elements = await section.locator('a').all();
    return elements.map(el => ({
      name: '',
      nameEn: el.textContent(),
      role: '编剧'
    }));
  } catch {
    return [];
  }
}

async function extractCast(page) {
  try {
    const elements = await page.locator('.cast_list tr').all();
    return elements.slice(1, 9).map(el => ({
      name: '',
      nameEn: el.locator('td:nth-child(2) a').textContent(),
      role: el.locator('td:nth-child(4)').textContent(),
      avatar: el.locator('td:nth-child(1) img').getAttribute('src')
    }));
  } catch {
    return [];
  }
}

async function extractOtherCast(page) {
  try {
    const elements = await page.locator('.cast_list tr').all();
    return elements.slice(9).map(el => ({
      name: '',
      nameEn: el.locator('td:nth-child(2) a').textContent(),
      role: el.locator('td:nth-child(4)').textContent()
    }));
  } catch {
    return [];
  }
}

async function extractProducer(page) {
  try {
    const section = await page.locator('#fullcredits_content').locator('h4[data-testid="producers"]');
    const elements = await section.locator('a').all();
    return elements.map(el => ({
      name: '',
      nameEn: el.textContent()
    }));
  } catch {
    return [];
  }
}

async function extractImageUrls(page) {
  try {
    const elements = await page.locator('.media_index_thumb_list img').all();
    return elements.map(el => el.getAttribute('src'));
  } catch {
    return [];
  }
}

async function extractVideos(page) {
  try {
    const elements = await page.locator('.video-item').all();
    return elements.map(el => ({
      title: el.locator('.video-title').textContent(),
      duration: el.locator('.video-duration').textContent(),
      thumbnail: el.locator('img').getAttribute('src'),
      url: el.locator('a').getAttribute('href')
    }));
  } catch {
    return [];
  }
}

async function extractSimilar(page) {
  try {
    const elements = await page.locator('.similar-title-item').all();
    return elements.map(el => ({
      title: el.locator('.title').textContent(),
      year: parseInt(el.locator('.year').textContent()),
      rating: parseFloat(el.locator('.rating').textContent())
    }));
  } catch {
    return [];
  }
}

// CLI 入口
if (require.main === module) {
  const args = require('minimist')(process.argv.slice(2));
  crawlImdb({
    id: args.id,
    output: args.output,
    timeout: args.timeout,
    verbose: args.verbose
  }).then(result => {
    console.log(`爬取完成: ${result.errors.length} 错误, ${result.warnings.length} 警告`);
  });
}

module.exports = { crawlImdb };