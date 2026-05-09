#!/usr/bin/env node

/**
 * Schema 字段查看工具
 * 
 * 用法：node tools/db/view-schema.mjs [表名]
 * 示例：node tools/db/view-schema.mjs Work
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 读取 schema.prisma
const schemaPath = path.join(__dirname, '../../prisma/schema.prisma');
const schemaContent = fs.readFileSync(schemaPath, 'utf-8');

// 解析 model
function parseModels(content) {
  const models = {};
  const lines = content.split('\n');
  
  let currentModel = null;
  let currentComment = [];
  let inModel = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 收集注释
    if (line.startsWith('///')) {
      currentComment.push(line.replace(/^\/\/\/\s?/, ''));
      continue;
    }
    
    // 开始 model
    if (line.startsWith('model ')) {
      const match = line.match(/model\s+(\w+)/);
      if (match) {
        currentModel = match[1];
        models[currentModel] = {
          comment: currentComment.join('\n'),
          fields: []
        };
        currentComment = [];
        inModel = true;
        continue;
      }
    }
    
    // 结束 model
    if (line === '}' && inModel) {
      inModel = false;
      currentModel = null;
      continue;
    }
    
    // 解析字段
    if (inModel && currentModel && line && !line.startsWith('//') && !line.startsWith('@@')) {
      const fieldMatch = line.match(/^(\w+)\s+(\w+)/);
      if (fieldMatch) {
        const [, name, type] = fieldMatch;
        const isOptional = line.includes('?');
        const hasDefault = line.includes('@default');
        
        models[currentModel].fields.push({
          name,
          type,
          optional: isOptional,
          hasDefault,
          comment: currentComment.join('\n')
        });
        currentComment = [];
      }
    }
    
    // 如果不是有效行，清空注释
    if (!line.startsWith('///') && line !== '') {
      currentComment = [];
    }
  }
  
  return models;
}

// 格式化输出
function printModel(modelName, model) {
  console.log('\n' + '='.repeat(80));
  console.log(`📊 ${modelName}`);
  console.log('='.repeat(80));
  
  if (model.comment) {
    console.log('\n📝 表说明：');
    console.log(model.comment);
  }
  
  console.log('\n📋 字段列表：\n');
  console.log('  字段名'.padEnd(25) + '类型'.padEnd(20) + '必填'.padEnd(8) + '说明');
  console.log('  ' + '-'.repeat(70));
  
  for (const field of model.fields) {
    const required = field.optional ? '否' : '是';
    const comment = field.comment ? field.comment.split('\n')[0] : '';
    console.log(
      '  ' + field.name.padEnd(23) + 
      field.type.padEnd(18) + 
      required.padEnd(8) + 
      comment
    );
    
    // 如果注释有多行，显示完整注释
    if (field.comment && field.comment.includes('\n')) {
      const lines = field.comment.split('\n');
      for (let i = 1; i < lines.length; i++) {
        console.log('  ' + ''.padEnd(51) + lines[i]);
      }
    }
  }
}

// 主函数
function main() {
  const models = parseModels(schemaContent);
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    // 显示所有表
    console.log('\n📚 所有数据表：\n');
    for (const [name, model] of Object.entries(models)) {
      const fieldCount = model.fields.length;
      const comment = model.comment ? model.comment.split('\n')[0] : '';
      console.log(`  ${name.padEnd(20)} (${fieldCount} 个字段) ${comment}`);
    }
    console.log('\n💡 使用 "node tools/db/view-schema.mjs <表名>" 查看详细字段');
    console.log('💡 例如: node tools/db/view-schema.mjs Work\n');
  } else {
    // 显示指定表
    const modelName = args[0];
    const model = models[modelName];
    
    if (!model) {
      console.error(`❌ 未找到表: ${modelName}`);
      console.log('\n可用的表：');
      Object.keys(models).forEach(name => console.log(`  - ${name}`));
      process.exit(1);
    }
    
    printModel(modelName, model);
  }
}

main();
