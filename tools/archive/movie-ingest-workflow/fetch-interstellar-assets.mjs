import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');
const movieAssetDir = path.join(repoRoot, 'site', 'public', 'assets', 'video', 'movie', '0101000006');
const peopleAssetDir = path.join(repoRoot, 'site', 'public', 'assets', 'people');

const posterUrls = [
  'https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@._V1_QL75_UX380_CR0,0,380,562_.jpg',
  'https://image.tmdb.org/t/p/original/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg',
  'https://image.tmdb.org/t/p/original/iawqQdFKI7yTUoSkDNP8gyV3J3r.jpg',
  'https://image.tmdb.org/t/p/original/7uCL4gbdmokTWyeYbJxwBo5pbVT.jpg',
  'https://image.tmdb.org/t/p/original/mS4EvhsrT0SQZOlWrQEzWI5KiUa.jpg'
];

const stillUrls = [
  'https://image.tmdb.org/t/p/original/2ssWTSVklAEc98frZUQhgtGHx7s.jpg',
  'https://image.tmdb.org/t/p/original/5XNQBqnBwPA9yT0jZ0p3s8bbLh0.jpg',
  'https://image.tmdb.org/t/p/original/65BTgbR7w8g5h8PlNwUgRVWqPyQ.jpg',
  'https://image.tmdb.org/t/p/original/8sNiAPPYU14PUepFNeSNGUTiHW.jpg',
  'https://image.tmdb.org/t/p/original/vgnoBSVzWAV9sNQUORaDGvDp7wx.jpg',
  'https://image.tmdb.org/t/p/original/l33oR0mnvf20avWyIMxW02EtQxn.jpg'
];

const peopleAssets = [
  { file: 'christopher-nolan.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/4/49/ChrisNolanBFI150224_%2810_of_12%29_%2853532289710%29_%28cropped2%29.jpg' },
  { file: 'jonathan-nolan.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/5/54/Jonathan_Nolan_at_SXSW_2024.jpg' },
  { file: 'matthew-mcconaughey.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/8/8c/Matthew_McConaughey_at_the_2025_Toronto_Film_Festival_%28Cropped%29.jpg' },
  { file: 'anne-hathaway.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/d/da/Anne_Hathaway-_Press_conference_for_the_film_%22The_Devil_Wears_Prada_2%22_-_55194764955_%28cropped%29.jpg' },
  { file: 'jessica-chastain.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/1/11/Jessica_Chastain-64631_%28cropped%29.jpg' },
  { file: 'michael-caine.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/3/3d/Michael_Caine_-_Viennale_2012_g_%28cropped%29.jpg' },
  { file: 'casey-affleck.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/e/e8/Casey_Affleck_at_the_Manchester_by_the_Sea_premiere_%2830199719155%29_%28cropped%29.jpg' },
  { file: 'wes-bentley.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/0/01/Wes_Bentley_The_Hunger_Games_premiere.jpg' },
  { file: 'mackenzie-foy.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/2/2c/Mackenzie_Foy_Cannes_2015.jpg' },
  { file: 'david-gyasi.jpg', url: 'https://media.themoviedb.org/t/p/original/4Kj6BI2Ki6tpAVzc4S6lh1Xzua3.jpg' },
  { file: 'bill-irwin.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/b/bb/Bill_Irwin_by_Gage_Skidmore.jpg' },
  { file: 'ellen-burstyn.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/6/63/Ellen_Burstyn_at_the_2009_Tribeca_Film_Festival.jpg' },
  { file: 'john-lithgow.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/5/52/John_Lithgow_at_Met_Opera_Opening_in_2008.jpg' },
  { file: 'timothee-chalamet.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/5/5c/Timoth%C3%A9e_Chalamet-63482_%28cropped%29.jpg' },
  { file: 'matt-damon.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/b/b4/MattDamon-byPhilipRomano.jpg' },
  { file: 'topher-grace.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/9/93/Topher_Grace_2019_by_Glenn_Francis_%283x4_cropped%29.jpg' },
  { file: 'josh-stewart.jpg', url: 'https://upload.wikimedia.org/wikipedia/commons/3/30/10.14.12JoshStewartByLuigiNovi1.jpg' }
];

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function downloadFile(url, targetPath) {
  const response = await fetch(url, {
    headers: {
      'user-agent': 'Mozilla/5.0'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to download ${url}: ${response.status}`);
  }

  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(targetPath, buffer);
}

async function main() {
  await fs.rm(movieAssetDir, { recursive: true, force: true });
  await ensureDir(movieAssetDir);
  await ensureDir(peopleAssetDir);

  for (let index = 0; index < posterUrls.length; index += 1) {
    const fileName = index === 0 ? 'poster-main.jpg' : `poster-${String(index).padStart(2, '0')}.jpg`;
    await downloadFile(posterUrls[index], path.join(movieAssetDir, fileName));
  }

  for (let index = 0; index < stillUrls.length; index += 1) {
    const fileName = `still-${String(index + 1).padStart(2, '0')}.jpg`;
    await downloadFile(stillUrls[index], path.join(movieAssetDir, fileName));
  }

  for (const asset of peopleAssets) {
    await downloadFile(asset.url, path.join(peopleAssetDir, asset.file));
  }

  console.log(JSON.stringify({
    posters: posterUrls.length,
    stills: stillUrls.length,
    people: peopleAssets.length
  }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
