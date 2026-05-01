/**
 * 百度百科 爬虫
 * 
 * 输入：电影名称
 * 输出：raw-baike.json
 */

const playwright = require('playwright');

async function crawlBaiduBaike(options) {
  const { title, output = 'raw-baike.json', timeout = 30000, verbose = false } = options;
  
  const searchUrl = `https://baike.baidu.com/item/${encodeURIComponent(title)}`;
  const crawledAt = new Date().toISOString();
  
  const result = {
    source: 'baike',
    sourceUrl: searchUrl,
    crawledAt,
    crawlerScript: 'baidu-baike.js',
    data: {},
    errors: [],
    warnings: []
  };
  
  const browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(timeout);
  
  try {
    // 1. 搜索并进入词条
    if (verbose) console.log('搜索百度百科...');
    await page.goto(searchUrl, { waitUntil: 'networkidle' });
    
    // 检查是否需要选择正确的词条
    const hasMultiple = await page.locator('.item-list').count() > 0;
    if (hasMultiple) {
      // 选择第一个匹配的影视类词条
      await page.locator('.item-list a').first().click();
      await page.waitForLoadState('networkidle');
    }
    
    result.sourceUrl = page.url();
    
    // 2. 提取基本信息
    if (verbose) console.log('提取基本信息...');
    
    result.data.title = await extractTitle(page);
    result.data.synopsis = await extractSynopsis(page);
    result.data.basicInfo = await extractBasicInfo(page);
    
    // 从基本信息中提取结构化数据
    const info = result.data.basicInfo;
    result.data.year = extractYearFromInfo(info);
    result.data.director = extractDirectorFromInfo(info);
    result.data.writer = extractWriterFromInfo(info);
    result.data.cast = extractCastFromInfo(info);
    result.data.genre = extractGenreFromInfo(info);
    result.data.country = extractCountryFromInfo(info);
    result.data.language = extractLanguageFromInfo(info);
    result.data.runtime = extractRuntimeFromInfo(info);
    
    // 3. 提取图片
    if (verbose) console.log('提取图片...');
    result.data.imageUrls = await extractImageUrls(page);
    
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

async function extractSynopsis(page) {
  try {
    const text = await page.locator('.lemma-summary').textContent();
    return { text: text.trim(), note: '' };
  } catch {
    return { text: '', note: '' };
  }
}

async function extractBasicInfo(page) {
  try {
    const elements = await page.locator('.basicInfo-item').all();
    const info = {};
    for (const el of elements) {
      const label = await el.locator('.basicInfo-block').textContent();
      const value = await el.locator('.basicInfo-block.value').textContent();
      info[label.trim()] = value.trim();
    }
    return info;
  } catch {
    return {};
  }
}

function extractYearFromInfo(info) {
  const keys = ['上映时间', '上映日期', '发行日期'];
  for (const key of keys) {
    if (info[key]) {
      const match = info[key].match(/\d{4}/);
      return match ? parseInt(match[0]) : null;
    }
  }
  return null;
}

function extractDirectorFromInfo(info) {
  const keys = ['导演', '执导'];
  for (const key of keys) {
    if (info[key]) {
      return info[key].split(/[,，、]/).map(name => ({
        name: name.trim(),
        nameEn: '',
        avatar: '',
        works: []
      }));
    }
  }
  return [];
}

function extractWriterFromInfo(info) {
  const keys = ['编剧', '原著', '改编'];
  for (const key of keys) {
    if (info[key]) {
      return info[key].split(/[,，、]/).map(name => ({
        name: name.trim(),
        nameEn: '',
        role: key
      }));
    }
  }
  return [];
}

function extractCastFromInfo(info) {
  const keys = ['主演', '演员', '配音'];
  for (const key of keys) {
    if (info[key]) {
      return info[key].split(/[,，、]/).map(name => ({
        name: name.trim(),
        nameEn: '',
        role: '',
        avatar: ''
      }));
    }
  }
  return [];
}

function extractGenreFromInfo(info) {
  const keys = ['类型', '题材'];
  for (const key of keys) {
    if (info[key]) {
      return info[key].split(/[,，、]/).map(s => s.trim());
    }
  }
  return [];
}

function extractCountryFromInfo(info) {
  const keys = ['制片国家', '国家', '地区'];
  for (const key of keys) {
    if (info[key]) {
      return info[key];
    }
  }
  return null;
}

function extractLanguageFromInfo(info) {
  const keys = ['语言', '对白语言'];
  for (const key of keys) {
    if (info[key]) {
      return info[key];
    }
  }
  return null;
}

function extractRuntimeFromInfo(info) {
  const keys = ['片长', '时长', '长度'];
  for (const key of keys) {
    if (info[key]) {
      const match = info[key].match(/(\d+)\s*分钟/);
      return match ? parseInt(match[1]) : null;
    }
  }
  return null;
}

async function extractImageUrls(page) {
  try {
    const elements = await page.locator('.lemma-picture img').all();
    return elements.map(el => el.getAttribute('src'));
  } catch {
    return [];
  }
}

// CLI 入口
if (require.main === module) {
  const args = require('minimist')(process.argv.slice(2));
  crawlBaiduBaike({
    title: args.title,
    output: args.output,
    timeout: args.timeout,
    verbose: args.verbose
  }).then(result => {
    console.log(`爬取完成: ${result.errors.length} 错误, ${result.warnings.length} 警告`);
  });
}

module.exports = { crawlBaiduBaike };