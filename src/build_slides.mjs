// CP6 deck from actual experiment CSVs. Run from repo root with Codex bundled
// Node and @oai/artifact-tool. Optional env: SLIDES_NODE_MODULES, SLIDES_SKILL_DIR,
// SLIDES_PYTHON, SLIDES_OUTPUT (use a new filename when rebuilding).
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const modules = process.env.SLIDES_NODE_MODULES ?? 'C:/Users/ADMIN/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const skill = process.env.SLIDES_SKILL_DIR ?? 'C:/Users/ADMIN/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
const python = process.env.SLIDES_PYTHON ?? 'C:/Users/ADMIN/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES ??= modules;
const { Presentation, PresentationFile, FileBlob } = await import(pathToFileURL(path.join(modules, '@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { resolvePresentationFont, applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const font = resolvePresentationFont();
const build = path.join(root, '.build/slides');
const finalPath = path.resolve(root, process.env.SLIDES_OUTPUT ?? 'report/slides/TOPIC_D.pptx');
await fs.mkdir(build, {recursive:true});
await fs.mkdir(path.dirname(finalPath), {recursive:true});
const raw = (await fs.readFile(path.join(root, 'results/obstacle_sweep.csv'), 'utf8')).trim().split(/\r?\n/);
const headers = raw.shift().split(',');
const rows = raw.map(line => Object.fromEntries(line.split(',').map((v,i)=>[headers[i], v])));
const failure = JSON.parse(await fs.readFile(path.join(root, 'results/failure_merge.json'), 'utf8'));
const hw = JSON.parse(await fs.readFile(path.join(root, 'results/hardware.json'), 'utf8'));
const p = Presentation.create({slideSize:{width:1280,height:720}});
const color = {ink:'#142D3B',blue:'#127A9C',orange:'#D57832',green:'#378467',muted:'#526874'};
function text(slide,value,x,y,w,h,size=28,bold=false,fill=color.ink) {
  const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value; shape.text.style={typeface:font,fontSize:size,bold,color:fill,autoFit:'none'};
  return shape;
}
function slide(title, notes) {
  const s=p.slides.add(); s.background.fill='#FFFFFF';
  text(s,title,48,32,1184,82,38,true);
  s.speakerNotes.textFrame.setText(notes);
  return s;
}
async function image(s,rel,x,y,w,h) {
  s.images.add({blob:new Uint8Array(await fs.readFile(path.join(root,rel))),contentType:'image/png',alt:rel,fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
const frames=['000008','000011','000049'];
const eps=rows.filter(r=>r.sweep==='eps');
const ground=rows.filter(r=>r.sweep==='distance_threshold');

let s=slide('Topic D · Phát hiện vật cản từ LiDAR',
  '0:00–0:30. Tống Trần Tiến Dũng, MSSV 2A202602791. Dữ liệu thật KITTI: 000008, 000011, 000049. Xem bốn bước từ trái qua phải. Trục x LiDAR hướng trước, y trái, z lên. Ground fit chỉ dùng điểm thấp để tránh chọn tường. Nguồn API: https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html. Ảnh: results/figures/obstacle_demo_000011.png.');
text(s,'Tống Trần Tiến Dũng · 2A202602791 · AI20K-T4',50,117,1180,42,24,false,color.muted);
text(s,'Voxel → RANSAC tách đất → DBSCAN → AABB từng cụm',50,165,1180,50,30,true,color.blue);
await image(s,'results/figures/obstacle_demo_000011.png',30,225,1220,420);
text(s,'ROI: x 1–40 m · |y| ≤ 15 m · voxel 0.15 m · seed 42',50,661,1180,34,22,false,color.muted);

s=slide('Tăng eps làm số cụm giảm ≥20% ở cả 3 frame',
  '0:30–1:05. Claim CP1 dự kiến ít nhất 2/3; đo được cả 3/3. Mỗi lần chỉ đổi eps, cố định voxel .15, ground .1, min_points 10, ROI và seed. Số cụm ít hơn không tương đương độ chính xác cao hơn. Noise cũng có thể ít hơn và nhiều vật bị nối thành một cụm. Source: results/obstacle_sweep.csv, sweep=eps.');
const chart=s.charts.add('line',{position:{left:42,top:159,width:790,height:480},
  categories:['0.3','0.5','0.8'],
  series:frames.map((frame,i)=>({name:frame,values:eps.filter(r=>r.frame===frame).map(r=>Number(r.n_clusters)),
    line:{fill:[color.blue,color.orange,color.green][i],width:3},marker:{symbol:'circle',size:8}})),
  hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:20}},
  xAxis:{title:{text:'DBSCAN eps (m)'},textStyle:{fontSize:20}},
  yAxis:{title:{text:'Số cụm'},min:0,textStyle:{fontSize:20}},
  chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF',lineOptions:{smooth:false}});
applyPresentationChartFont(chart,{fontFamily:font});
let yy=190;
for(const frame of frames) {
  const g=eps.filter(r=>r.frame===frame); const a=Number(g[0].n_clusters), b=Number(g[2].n_clusters);
  text(s,`${frame}: ${a} → ${b}`,870,yy,350,54,30,true);
  text(s,`Giảm ${(100*(1-b/a)).toFixed(1)}%`,870,yy+55,350,50,26,false,color.blue);
  yy+=134;
}
text(s,'Cố định RANSAC 0.1 m · min_points 10 · voxel 0.15 m',50,656,1180,40,24,false,color.muted);

s=slide('Ngưỡng mặt đất thay đổi điểm giữ lại và số cụm',
  `1:05–1:40. Quét threshold độc lập .05/.1/.3, cố định eps=.5. Frame000008 có số cụm tăng 32 lên39 khi điểm giữ lại giảm, vì loại điểm cầu nối có thể tách cụm. Kích thước từng AABB nằm trong obstacle_clusters.csv. Latency bỏ warm-up và đo20 lần mỗi cấu hình, p50/p95 không gồm IO/plot/GT. CPU ${hw.cpu}, RAM ${hw.ram_gib}GiB, OMP1, không GPU. Source: results/obstacle_sweep.csv and results/obstacle_latency.csv.`);
const values=[['Frame','Đất (m)','Điểm giữ','Số cụm','Gần (m)','p50 (ms)'],
  ...ground.map(r=>[r.frame,Number(r.distance_threshold).toFixed(2),r.n_obstacle,r.n_clusters,Number(r.nearest_m).toFixed(2),Number(r.latency_p50_ms).toFixed(1)])];
const table=s.tables.add({rows:values.length,columns:6,left:58,top:146,width:1164,height:418,columnWidths:[194,180,210,180,200,200],values});
table.borders.assign({fill:'#D5E0E5',width:1,style:'solid'});
for(let r=0;r<values.length;r++) for(let c=0;c<6;c++) {
  const cell=table.getCell(r,c); cell.fill=r===0?color.ink:(r%2===0?'#EFF5F7':'#FFFFFF');
  cell.text.style={typeface:font,fontSize:23,color:r===0?'#FFFFFF':color.ink,bold:r===0};
}
text(s,'Đổi riêng RANSAC · giữ eps 0.5 m, voxel 0.15 m, min_points 10',58,600,1164,42,25,false,color.blue);
text(s,'360 lượt đo · 20 lượt/cấu hình sau warm-up · p50/p95 trong REPORT',58,652,1164,42,24,false,color.muted);

s=slide('Failure: hai người có cùng cụm trội khi eps = 0.8 m',
  '1:40–2:20. KITTI000011 GT#0 và#1 ở13.41/14.48m. Thí nghiệm riêng dùng min_points5 ở cả hai bên, benchmark dùng10; chỉ thay eps .5→.8. Cụm trội táchC7/C47 với61/8 điểm; sau đó cùngC5 với61/13. Baseline không hoàn hảo: một số điểm của người thứ2 đã vào cụm khác. Lỗi Preprocess do kết nối mật độ, không phải calibration hay Time. Gộp instance không đồng nghĩa đường trống. Source: results/failure_merge.csv, results/failure_merge.json.');
await image(s,'results/figures/fail_01_dbscan_merge_pedestrians.png',38,136,1204,495);
text(s,'Preprocess · min_points = 5 ở cả hai cấu hình · seed/ROI/voxel/ground cố định',50,656,1180,40,23,false,color.muted);

s=slide('Triển khai robot kho: theo dõi latency và lỗi tách cụm',
  '2:20–3:00. Khởi đầu thử .15m voxel/.1ground/.5eps, chưa chứng nhận an toàn. Đề xuất robot chậm .5m/s. Log plane tilt, n_roi, noise, cluster extent, nearest và p95. Đất .3 có thể bỏ vật thấp, cần test pallet/người ngồi trên log kho. Cờ p95>200ms hoặc fit lỗi thì giảm tốc/dừng kiểm tra; nearest phải trừ footprint và dùng quãng đường phanh. Chạy python-m src.experiment, src.failure, check_submission. Occupancy ô vắng là unknown. Nguồn: REPORT mục4 và results/hardware.json. Học viên cần tự đọc và giải thích code; AI đã được khai báo.');
text(s,'Cấu hình khởi đầu',56,145,1150,50,30,true,color.blue);
text(s,'voxel 0.15 m · RANSAC 0.1 m · eps 0.5 m\nKiểm thử thêm vật thấp, sàn dốc và LiDAR của robot',56,205,1150,110,30);
text(s,'Log khi chạy thật',56,343,1150,48,30,true,color.blue);
text(s,'plane/tilt · mật độ điểm · số/kích thước cụm · nearest_m · p95\nFit lỗi, tilt >20° hoặc p95 >200 ms: cờ giảm tốc/kiểm tra',56,403,1150,110,28);
text(s,'Chạy lại và demo',56,538,1150,48,30,true,color.blue);
text(s,'python -m src.experiment    |    python -m src.failure\npython tools/check_submission.py',56,594,1150,92,26);

const candidatePath=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
await finalizePresentation({workspaceDir:root,candidatePath,finalPath,
  pythonExecutable:python,
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','3'],
  explicitTotalSlideCount:5,requiredNativeTableOwnerSlides:[3],requiredNativeChartOwnerSlides:[2],
  materializeLiteralChartWorkbooks:true,
  fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
  receiptPath:path.join(build,`${path.basename(path.dirname(finalPath))}.validation.json`)});
const finalDeck = await PresentationFile.importPptx(await FileBlob.load(finalPath));
for(let i=0;i<finalDeck.slides.items.length;i++) {
  const png=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log(`Created ${finalPath}; font ${font}; 5 slides`);
