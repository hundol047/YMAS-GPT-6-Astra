import {defineConfig} from 'vitest/config';
export default defineConfig({test:{environment:'jsdom',setupFiles:['./tests/setup.js'],testTimeout:15000,fileParallelism:false,pool:'forks',maxWorkers:1}});
