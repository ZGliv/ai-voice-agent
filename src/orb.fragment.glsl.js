/** The original procedural orb, with directional shading to retain its volume at rest. */
export const fragmentShader = `
uniform float time;
uniform float amplitude;
uniform vec3 baseColor;
varying vec3 vNormal;
void main() {
  vec3 n = normalize(vNormal);
  vec3 light = normalize(vec3(-0.6, 0.8, 1.2));
  float diffuse = max(dot(n, light), 0.0);
  float rim = pow(1.0 - max(n.z, 0.0), 2.5);
  float sheen = pow(max(dot(reflect(-light, n), vec3(0.0,0.0,1.0)),0.0),35.0);
  float ripple = sin(n.y * 18.0 + n.x * 5.0 + time) * 0.025 * amplitude;
  vec3 color = baseColor * (0.18 + diffuse * 0.95 + ripple);
  color += vec3(0.13,0.32,0.6) * rim * 0.42 + vec3(0.3,0.55,0.9) * sheen * 0.55;
  gl_FragColor = vec4(pow(max(color,vec3(0.0)),vec3(0.4545)),0.98);
}
`;
