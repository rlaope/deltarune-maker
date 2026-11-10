import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const assetRoot = resolve(process.env.QUEEN_ASSET_DIR || fileURLToPath(new URL('./assets/', import.meta.url)));
